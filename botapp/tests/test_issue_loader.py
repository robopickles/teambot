from django.test import TestCase

from botapp.enums import IssueSystem, ServiceType
from botapp.models import ServiceAccount, UserProfile
from botapp.trackers import IssueLoader


class TestBatchImport(TestCase):
    def setUp(self):
        user1 = UserProfile.objects.create(name='user1')
        self.user1 = ServiceAccount.objects.create(
            user_profile=user1, uid='user1', service_type=ServiceType.jira
        )

    def test_parse_issue(self):
        system, issue_id = IssueLoader().parse_issue('BACK-193: hello world')
        assert system == IssueSystem.jira, system
        assert issue_id == 'BACK-193', issue_id

    def test_parse_issue2(self):
        system, issue_id = IssueLoader().parse_issue('back-193: hello world')
        assert system == IssueSystem.jira, system
        assert issue_id == 'BACK-193', issue_id

    def test_parse_issue3(self):
        system, issue_id = IssueLoader().parse_issue('[iOS-193] hello world')
        assert system == IssueSystem.jira, system
        assert issue_id == 'IOS-193', issue_id

    def test_parse_issue4(self):
        system, issue_id = IssueLoader().parse_issue('[WEB-193] hello world')
        assert system == IssueSystem.jira, system
        assert issue_id == 'WEB-193', issue_id

    def test_parse_issue7(self):
        issue = IssueLoader().parse_issue('[ABC-193] hello world')
        assert issue is None, issue
