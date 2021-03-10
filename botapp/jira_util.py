import os
from functools import cached_property

import requests
from django.conf import settings

from botapp.enums import IssueSystem
from botapp.models import Issue


LOGIN_URL = '{}/rest/auth/latest/session'.format(settings.JIRA_BASE_URL)
CUSTOM_ETA_FIELD = os.environ.get('CUSTOM_ETA_FIELD', 'customfield_10035')


class JiraFetcher:
    @cached_property
    def auth(self):
        return (os.environ['JIRA_USER'], os.environ['JIRA_TOKEN'])

    @cached_property
    def api_url(self):
        return f'{settings.JIRA_BASE_URL}/rest/api/latest'

    def fetch_jira_issue(self, issue_id):
        s = requests.session()
        issue_url = '{}/rest/api/latest/issue/{}'.format(settings.JIRA_BASE_URL, issue_id)
        j = s.get(issue_url, auth=self.auth).json()
        return j

    def iter_worklogs(self, session, values):
        for item in values:
            worklog_id = item['worklogId']
            updated = item['updatedTime']
            resp = session.post(
                f'{self.api_url}/worklog/list', json={'ids': [worklog_id]}, auth=self.auth
            )
            assert resp.status_code == 200, (resp, resp.reason)
            resp = resp.json()
            for i in resp:
                yield resp[0], updated

    def fetch_worklogs(self, start, end):
        with requests.session() as session:
            start_unix = int(start.timestamp() * 1000)
            end_unix = int(end.timestamp() * 1000)
            last = None
            while not last:
                resp = session.get(
                    f'{settings.JIRA_BASE_URL}/rest/api/latest/worklog/updated',
                    auth=self.auth,
                    params={'since': start_unix},
                ).json()
                last = resp['lastPage']
                start_unix = resp['until']
                for i, updated in self.iter_worklogs(session, resp['values']):
                    if updated > end_unix:
                        return
                    yield i

    def get_original_estimate(self, issue_dict):
        tt = issue_dict.get('fields', {}).get('timetracking', {})
        orig_estimate_sec = tt.get('originalEstimateSeconds')
        if orig_estimate_sec is not None:
            return orig_estimate_sec / 3600

        orig_eta_hours = issue_dict.get('fields', {}).get(CUSTOM_ETA_FIELD)
        if orig_eta_hours:
            return orig_eta_hours

    def create_jira_issue(self, issue_id):
        j = self.fetch_jira_issue(issue_id)
        if 'fields' in j:
            description = j['fields']['description']
            summary = j['fields']['summary']
            print('creating issue: {}'.format(issue_id))
            return Issue.objects.create(
                issue_system=IssueSystem.jira,
                issue_id=issue_id,
                title=summary,
                description=description or '',
                original_estimate=self.get_original_estimate(j),
                url='{}/browse/{}'.format(settings.JIRA_BASE_URL, issue_id),
            )

    def update_jira_issue(self, issue, issue_id):
        j = self.fetch_jira_issue(issue_id)
        if 'fields' in j:
            print('updating issue: {}'.format(issue_id))

            description = j['fields']['description']
            summary = j['fields']['summary']

            issue.title = summary
            issue.description = description or ''
            issue.original_estimate = self.get_original_estimate(j)
            issue.save()
