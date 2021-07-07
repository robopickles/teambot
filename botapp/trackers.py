import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import cached_property

import pytz
import requests
import upwork
from django.conf import settings
from django.utils import timezone
from django_orm_sugar import Q

from botapp.enums import IssueSystem, ServiceType, WorklogSystem
from botapp.factories import ServiceAccountFactory
from botapp.jira_util import JiraFetcher
from botapp.models import Issue, ServiceAccount, UserProfile, Worklog


class IssueLoader:
    def __init__(self, autoupdate=False):
        self.issues_dict = {}
        self.autoupdate = autoupdate

    def parse_issue(self, description):
        pattern = r'|'.join([r'({}-\d+)'.format(t) for t in settings.JIRA_PROJECT_KEYS])
        matched = re.search(pattern, description, re.IGNORECASE)
        if matched:
            return IssueSystem.jira, matched.group(0).upper()

    def get_issue_failsafe(self, memo):
        try:
            issue = self.get_issue(memo)
        except Exception as e:
            logging.exception(e)
            issue = None
        return issue

    def get_issue(self, description):
        issue_tuple = self.parse_issue(description)

        if issue_tuple:
            issue_system, issue_id = issue_tuple

            # try cached issue
            issue = self.issues_dict.get(issue_tuple)
            if issue:
                print('found cached issue: {}'.format(issue_id))
                return issue

            if issue_system == IssueSystem.jira:
                issue = Issue.objects.filter(issue_system=issue_system, issue_id=issue_id).first()

                if issue:
                    if self.autoupdate:
                        JiraFetcher().update_jira_issue(issue, issue_id)
                else:
                    issue = JiraFetcher().create_jira_issue(issue_id)

                # cache issue
                self.issues_dict[issue_tuple] = issue

                return issue


class BaseWorklogLoader(ABC):
    worklog_system: WorklogSystem
    service_type: ServiceType
    log = logging.getLogger('django.server')
    drop_old = False

    def __init__(self, command=None):
        self.command = command

    def print_success(self, text):
        if self.command:
            self.command.stdout.write(self.command.style.SUCCESS(text))
        else:
            print(text)

    def print_error(self, text):
        if self.command:
            self.command.stderr.write(self.command.style.ERROR(text))
        else:
            print(text)

    def sync(self, from_date, to_date):
        report = self.fetch_team_report(from_date, to_date)
        if report is not None:
            self.sync_fetched_report(from_date, to_date, report)

    def sync_fetched_report(self, from_date, to_date, report):
        self.log.info(
            'Sync report {} from {} to {}'.format(self.worklog_system.name, from_date, to_date)
        )

        batch = []

        if self.drop_old:
            Worklog.objects.filter(
                Q.work_date >= from_date,
                Q.work_date <= to_date,
                Q.worklog_system == self.worklog_system,
            ).delete()

        issue_loader = IssueLoader(autoupdate=True)
        for (
            uniq_id,
            user_id,
            user_name,
            work_date,
            hours,
            memo,
            dt_range,
        ) in self.iter_fetched_report(report):
            service_account = ServiceAccount.objects.filter(
                service_type=self.service_type, uid=user_id
            ).first()

            user_profile = service_account.user_profile if service_account else None

            issue = issue_loader.get_issue_failsafe(memo)

            if work_date < from_date or work_date > to_date:
                print(f'SKIP: {user_name} {memo} {work_date=} {from_date=} {to_date=}')
                continue

            defaults = dict(
                work_date=work_date,
                user_id=user_id,
                user_name=user_name,
                hours=hours,
                description=memo,
                issue=issue,
                from_datetime=dt_range[0],
                to_datetime=dt_range[1],
                worklog_system=self.worklog_system,
                user_profile=user_profile,
            )
            worklog, created = Worklog.objects.update_or_create(uniq_id=uniq_id, defaults=defaults)
            self.log.info(
                u'worklog: {} {}, {}, {}, {}, {}, {}'.format(
                    uniq_id, user_id, user_name, work_date, hours, memo, dt_range
                )
            )
            batch.append(worklog)
        if not self.drop_old:
            all_worklogs = Worklog.objects.filter(
                Q.work_date >= from_date,
                Q.work_date <= to_date,
                Q.worklog_system == self.worklog_system,
            )
            ids = set(x.id for x in batch)

            for wl in all_worklogs:
                if wl.id not in ids:
                    wl.delete()

        print('synced {} worklogs'.format(len(batch)))

    @abstractmethod
    def iter_fetched_report(self, report):
        raise NotImplementedError()

    @abstractmethod
    def fetch_team_report(self, from_date, to_date):
        raise NotImplementedError()


class UpworkLoader(BaseWorklogLoader):
    worklog_system = WorklogSystem.upwork
    service_type = ServiceType.upwork
    drop_old = True

    def fetch_team_report(self, from_date, to_date):
        client = upwork.Client(
            os.environ['UPWORK_PUBLIC_KEY'],
            os.environ['UPWORK_SECRET_KEY'],
            oauth_access_token=os.environ['UPWORK_OAUTH_TOKEN'],
            oauth_access_token_secret=os.environ['UPWORK_OAUTH_TOKEN_SECRET'],
        )
        pattern = '%Y-%m-%d'
        fd = from_date.strftime(pattern)
        td = to_date.strftime(pattern)

        query = (
            "SELECT worked_on, provider_id, provider_name, sum(hours), memo "
            "WHERE worked_on >= '{}' AND worked_on <= '{}'".format(fd, td)
        )
        report = client.timereport.get_team_report(
            settings.UPWORK_COMPANY_ID, settings.UPWORK_TEAM_ID, query
        )
        if report.get('status', 'success') == 'success':
            return report
        else:
            raise RuntimeError(report)

    def iter_fetched_report(self, report):
        for row in report['table']['rows']:
            work_date = datetime.strptime(self.get_col(row, 0), '%Y%m%d').date()
            user_id = self.get_col(row, 1)
            user_name = self.get_col(row, 2)
            hours = float(self.get_col(row, 3))
            memo = self.get_col(row, 4)

            if memo == 'No memo':
                memo = ''

            dt_range = (None, None)
            yield None, user_id, user_name, work_date, hours, memo, dt_range

    def get_col(self, upwork_row, index):
        """
        Upwork columns are in format below:

        {u'c':
            [{u'v': u'20170307'},
            {u'v': u'username'},
            {u'v': u'Dmytro Zavgorodniy'},
            {u'v': u'8.833333'}]
        }
        """
        return upwork_row['c'][index]['v']


class SMonLoader(BaseWorklogLoader):
    """
    SMon - screenshot monitor loader
    """

    worklog_system = WorklogSystem.smon
    service_type = ServiceType.smon

    drop_old = True

    def iter_fetched_report(self, report):
        for d in report:
            from_time = d['from']
            to_time = d['to']

            work_date = datetime.fromtimestamp(from_time, tz=timezone.utc).date()
            user_id = d['employmentId']
            user_name = ''
            hours = (to_time - from_time) / 3600.0
            memo = d['note']
            dt_range = (
                datetime.fromtimestamp(from_time, timezone.utc),
                datetime.fromtimestamp(to_time, timezone.utc),
            )
            yield None, user_id, user_name, work_date, hours, memo, dt_range

    def fetch_team_report(self, from_date, to_date):
        token = os.environ.get('SMON_TOKEN', '')

        if not token:
            logging.warning("SMON_TOKEN env variable is not set")

        headers = {'X-SSM-Token': token, 'Accept': 'application/json'}

        from_timestamp = int(from_date.strftime('%s'))
        to_timestamp = int((to_date + timedelta(1)).strftime('%s'))

        data = []
        for s in ServiceAccount.objects.filter(service_type=ServiceType.smon):
            data.append({"employmentId": s.uid, "from": from_timestamp, "to": to_timestamp})

        if data:
            r = requests.post(
                'https://screenshotmonitor.com/api/v2/GetActivities', json=data, headers=headers
            )
            if r.status_code == 200:
                return r.json()
            else:
                raise Exception(
                    'Screenshot Monitor failed to sync with errors: {}, {}'.format(
                        r.status_code, r.content
                    )
                )


class AccountCreator(UpworkLoader):
    log = logging.getLogger('django.server')

    def sync_fetched_report(self, from_date, to_date, report):
        for row in report['table']['rows']:
            user_id = self.get_col(row, 1)
            user_name = self.get_col(row, 2)

            profile, created = UserProfile.objects.get_or_create(name=user_name)
            if created:
                self.log.info('Created profile {}'.format(profile))

            service_account, created = ServiceAccount.objects.get_or_create(
                service_type=ServiceType.upwork, uid=user_id, user_profile=profile
            )


class JiraLoader(BaseWorklogLoader):
    worklog_system = WorklogSystem.jira
    service_type = ServiceType.jira
    autocreate_users = os.environ.get('JIRA_AUTOCREATE_USERS', '0') == '1'

    @cached_property
    def jf(self):
        return JiraFetcher()

    def fetch_team_report(self, from_date, to_date):
        start = datetime.fromordinal(from_date.toordinal())
        end = datetime.fromordinal(to_date.toordinal()) + timedelta(days=1)
        report = list(self.jf.fetch_worklogs(start, end))
        return report

    def create_users(self, users):
        for uid, name in users.items():
            ServiceAccountFactory(uid=uid, service_type=ServiceType.jira, user_profile__name=name)

    def iter_fetched_report(self, report):
        if self.autocreate_users:
            users = {
                item['updateAuthor']['accountId']: item['updateAuthor']['displayName']
                for item in report
            }
            self.create_users(users)

        for item in report:
            print(f'Item: {item}')
            work_date = (
                datetime.strptime(item['updated'], '%Y-%m-%dT%H:%M:%S.%f%z')
                .astimezone(pytz.utc)
                .date()
            )
            user_id = item['updateAuthor']['accountId']
            user_name = item['updateAuthor']['displayName']
            hours = float(item['timeSpentSeconds'] / 60 / 60)
            issue = self.jf.fetch_jira_issue(item['issueId'])
            memo = issue['key']
            if comment := item.get('comment'):
                memo += f': {comment}'

            dt_range = (None, None)
            yield item['id'], user_id, user_name, work_date, hours, memo, dt_range
