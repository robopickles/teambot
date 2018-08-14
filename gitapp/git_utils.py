import logging
from pprint import pprint

import os

import requests
from dateutil.parser import parse as parse_date
from datetime import datetime

from django.utils import timezone

from botapp.enums import GitHosting, ServiceType
from botapp.models import ServiceAccount
from botapp.trackers import IssueLoader
from gitapp.models import GitProject, GitCommit


class GitLabClient:
    """
    Alternative client, which will support pipeline schedules
    """
    DATE_PATTERN = "%Y-%m-%d"

    def __init__(self):
        self.host = os.environ.get('GITLAB_HOST', '')
        self.token = os.environ.get('GITLAB_TOKEN', '')

        if not self.host:
            logging.warning('GITLAB_HOST env variable is not set!')

        if not self.token:
            logging.warning('GITLAB_TOKEN env variable is not set!')

        self.api_version = '4'

    def list_pipeline_schedules(self, project_id):
        path = 'projects/{}/pipeline_schedules'.format(project_id)
        return self.fetch_path(path)

    def get_pipeline_schedule(self, project_id, schedule_id):
        path = 'projects/{}/pipeline_schedules/{}'.format(project_id, schedule_id)
        return self.fetch_path(path)

    def list_recent_commits(self, project_id, from_date, to_date):
        since = from_date.strftime(self.DATE_PATTERN)
        for branch in self.fetch_path('/projects/{}/repository/branches'.format(project_id),
                                      {'per_page': 1000}):
            branch_name = branch['name']
            if parse_date(branch['commit']['committed_date']).date() >= from_date:
                branch_name = branch['name']
                for commit in self.fetch_path('/projects/{}/repository/commits'.format(project_id),
                                              {'since': since, 'ref_name': branch_name}):
                    yield branch_name, commit

    def get_commit_stats(self, project_id, commit_id):
        try:
            return self.fetch_path('/projects/{}/repository/commits/{}'
                                   .format(project_id, commit_id))['stats']
        except Exception as e:
            print('Failed to fetch commit {} for project {}'.format(commit_id, project_id))
            raise e

    def fetch_path(self, path, params={}):
        url = '{}/api/v{}/{}'.format(self.host, self.api_version, path.lstrip('/'))
        r = requests.get(url, params=params, headers={'Private-Token': self.token})
        if r.status_code == 200:
            return r.json()
        else:
            raise Exception(r.content)


class GitlabLoader:
    def __init__(self):
        # custom client
        self.client = GitLabClient()
        self.issue_loader = IssueLoader()

    def sync(self, from_date, to_date):
        for project in GitProject.objects.filter(hosting=GitHosting.gitlab):
            for br, commit in self.client.list_recent_commits(project.project_id,
                                                              from_date, to_date):
                c = GitCommit.objects.filter(hash=commit['id']).first()
                if c:
                    print('{} already imported "{}"'.format(c.short_id, c.title))

                else:
                    print('{} importing "{}"'.format(commit['short_id'], commit['title']))
                    issue = self.issue_loader.get_issue(commit['title'])

                    stats = self.get_commit_stats(project.project_id, commit['short_id'])
                    c = GitCommit(hash=commit['id'],
                                  created_at=parse_date(commit['created_at']),
                                  short_id=commit['short_id'],
                                  title=commit['title'],

                                  author_name=commit['author_name'],
                                  author_email=commit['author_email'],
                                  authored_date=parse_date(commit['authored_date']),

                                  committer_name=commit['committer_name'],
                                  committer_email=commit['committer_email'],
                                  committed_date=parse_date(commit['committed_date']),

                                  project=project,
                                  issue=issue,

                                  author_profile=self.get_user_profile(commit['author_email']),
                                  committer_profile=self.get_user_profile(
                                      commit['committer_email']),

                                  message=commit['message'],

                                  additions=stats['additions'],
                                  deletions=stats['deletions'],
                                  total=stats['total'])
                    c.save()

    def get_commit_stats(self, project_id, commit_id):
        return self.client.get_commit_stats(project_id, commit_id)

    def get_user_profile(self, uid):
        service_account = ServiceAccount.objects.filter(uid=uid, service_type=ServiceType.gitlab) \
            .first()
        if service_account:
            return service_account.user_profile

    def get_pipeline_schedules(self, project_id):
        schedules = self.client.list_pipeline_schedules(project_id)
        results = []
        for s in schedules:
            extended = self.client.get_pipeline_schedule(project_id, s['id'])
            results.append(extended)
        return results
