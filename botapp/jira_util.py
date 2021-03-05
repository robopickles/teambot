import os

import requests
from django.conf import settings

from botapp.enums import IssueSystem
from botapp.models import Issue


LOGIN_URL = '{}/rest/auth/latest/session'.format(settings.JIRA_BASE_URL)
CUSTOM_ETA_FIELD = os.environ.get('CUSTOM_ETA_FIELD', 'customfield_10035')


class JiraFetcher:
    def fetch_jira_issue(self, issue_id):
        s = requests.session()
        issue_url = '{}/rest/api/latest/issue/{}'.format(settings.JIRA_BASE_URL, issue_id)
        j = s.get(issue_url, auth=(os.environ['JIRA_USER'], os.environ['JIRA_TOKEN'])).json()
        return j

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
