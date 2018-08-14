from datetime import datetime
from django.test import TestCase
from mock import patch

from botapp.enums import ServiceType, GitHosting
from botapp.models import ServiceAccount, UserProfile
from gitapp.git_utils import GitlabLoader
from gitapp.models import GitProject, GitCommit
from gitapp.tests.fixtures import list_recent_commits


class TestImportGitlab(TestCase):
    def setUp(self):
        self.dev1 = UserProfile.objects.create(name='dev1')
        self.dev2 = UserProfile.objects.create(name='dev2')
        self.dev3 = UserProfile.objects.create(name='dev3')

        self.project = GitProject.objects.create(project_id=1,
                                                 name='my-project',
                                                 hosting=GitHosting.gitlab)

        for i, dev in enumerate([self.dev1, self.dev2, self.dev3]):
            ServiceAccount.objects.create(user_profile=dev,
                                          uid='jira-{}'.format(i + 1),
                                          service_type=ServiceType.jira)
            ServiceAccount.objects.create(user_profile=dev,
                                          uid='gitlab-{}@gettipsi.com'.format(i + 1),
                                          service_type=ServiceType.gitlab)

        self.patcher = patch('gitapp.git_utils.GitLabClient.list_recent_commits',
                             return_value=list_recent_commits())
        self.patcher.start()

        self.patcher2 = patch('gitapp.git_utils.GitlabLoader.get_commit_stats',
                              return_value={'additions': 7,
                                            'deletions': 3,
                                            'total': 10})
        self.patcher2.start()

    def test_import_commits_created(self):
        today = datetime.today()
        GitlabLoader().sync(today, today)

        count = GitCommit.objects.all().count()
        assert count == 3, count

    def test_commit_author(self):
        today = datetime.today()
        GitlabLoader().sync(today, today)

        commit = GitCommit.objects.filter(hash='3da541559918a808c2402bba5012f6c60b27661c').first()
        assert commit, commit

        assert commit.author_profile, commit.author_profile
        assert commit.author_profile.id == self.dev1.id, commit.author_profile

    def test_commit_committer(self):
        today = datetime.today()
        GitlabLoader().sync(today, today)

        commit = GitCommit.objects.filter(hash='3da541559918a808c2402bba5012f6c60b27661c').first()
        assert commit, commit

        assert commit.committer_profile, commit.committer_profile
        assert commit.committer_profile.id == self.dev2.id, commit.committer_profile

    def test_unknown_committers(self):
        today = datetime.today()
        GitlabLoader().sync(today, today)

        commit = GitCommit.objects.filter(hash='b75013a2ab5822b00e7ada00389c69f4ea565f68').first()
        assert commit, commit

        assert commit.committer_profile is None
        assert commit.author_profile is None

    def tearDown(self):
        self.patcher.stop()
        self.patcher2.stop()
