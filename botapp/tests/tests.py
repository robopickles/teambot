from datetime import date, datetime, timedelta
from pprint import pprint

from django.test import TestCase
from mock import patch, MagicMock

from agileapp.views import RenderReport, SummaryParser
from botapp.actions import IssueAction, ReportAction
from botapp.enums import ServiceType, IssueSystem, WorklogSystem
from botapp.models import UserProfile, ServiceAccount, Issue, Worklog, Team
from botapp.trackers import UpworkLoader, SMonLoader
from botapp.views import iterate_dates
from .fixtures import get_upwork_report, get_smon_report, load_jira_issue


class TestUpwork(TestCase):
    def setUp(self):
        team = Team.objects.create(name='Default', default=True)
        for upwork_id, username in (['jsmith', 'John Smith'],
                                    ['vpupkin', 'Vasya Pupkin']):
            u = UserProfile.objects.create(name=username)
            team.user_profiles.add(u)
            ServiceAccount.objects.create(user_profile=u, service_type=ServiceType.upwork,
                                          uid=upwork_id)

        for issue in ['IOS-96', 'WEB-336', 'IOS-838']:
            Issue.objects.create(issue_system=IssueSystem.jira,
                                 issue_id=issue,
                                 title=issue,
                                 description=issue)
        self.upwork_patcher = patch('botapp.trackers.UpworkLoader.fetch_team_report',
                                    return_value=get_upwork_report())
        self.jira_patcher = patch('botapp.trackers.JiraFetcher.fetch_jira_issue',
                                  return_value=load_jira_issue('IOS-153'))
        self.patchers = [self.upwork_patcher, self.jira_patcher]

        # start patchers
        [p.start() for p in self.patchers]

    def test_upwork_mock(self):
        loader = UpworkLoader()
        today = date.today()
        report = loader.fetch_team_report(today, today)
        assert report['server_time'] == 1489659419, report

    def test_upwork_loader(self):
        UpworkLoader().sync(date.today(), date.today())
        worklogs = Worklog.objects.filter(worklog_system=WorklogSystem.upwork).count()
        assert worklogs == 5, worklogs

    def test_jira_issue_creation(self):
        UpworkLoader().sync(date.today(), date.today())

        # JIRA issue RNA-153 has to be fetched automatically
        i = Issue.objects.filter(issue_system=IssueSystem.jira, issue_id='IOS-153').first()

        self.assertIsNotNone(i)
        self.assertAlmostEqual(i.original_estimate, 8)

    def test_jira_issue_update(self):
        i = Issue.objects.create(issue_system=IssueSystem.jira, issue_id='IOS-153')
        UpworkLoader().sync(date.today(), date.today())

        # JIRA issue RNA-153 has to be updated automatically
        i = Issue.objects.filter(issue_system=IssueSystem.jira, issue_id='IOS-153').first()

        self.assertIsNotNone(i)
        self.assertAlmostEqual(i.original_estimate, 8)


    def test_send_issues_console(self):
        msg = IssueAction().handle_dates(date.today(), date.today(), {'sync': True,
                                                                      'output': 'console'})
        self.assertEqual(msg.strip(), """Total hours of tracked time without memo:
John Smith....0.2h""")

    def test_send_report_console(self):
        msg = ReportAction().handle_dates(date.today(), date.today(), {'sync': True, 'output': 'console'})
        self.assertEqual(msg.strip(), """John Smith.....0.2h
Vasya Pupkin...2.0h""")

    def tearDown(self):
        # stop patchers
        [p.stop() for p in self.patchers]


class TestSMon(TestCase):
    def setUp(self):
        for smon_user_id, username in (['72690', 'John Smith'],
                                       ['72691', 'Vasya Pupkin']):
            u = UserProfile.objects.create(name=username)
            ServiceAccount.objects.create(user_profile=u, service_type=ServiceType.smon,
                                          uid=smon_user_id)

        for issue in ['IOS-96', 'BACK-813', 'WEB-336', 'IOS-838']:
            Issue.objects.create(issue_system=IssueSystem.jira,
                                 issue_id=issue,
                                 title=issue,
                                 description=issue)

        self.smon_patcher = patch('botapp.trackers.SMonLoader.fetch_team_report',
                                  return_value=get_smon_report())
        self.jira_patcher = patch('botapp.trackers.JiraFetcher.fetch_jira_issue',
                                  return_value=load_jira_issue('IOS-153'))

        self.patchers = [self.smon_patcher, self.jira_patcher]

        # start patchers
        [p.start() for p in self.patchers]

    def test_worklog_count(self):
        SMonLoader().sync(date.today(), date.today())
        worklogs = Worklog.objects.filter(worklog_system=WorklogSystem.smon).count()
        assert worklogs == 3, worklogs

    def test_upwork_worklogs_not_daleted(self):
        Worklog.objects.create(work_date=date.today(),
                               user_id='abc',
                               user_name='abc',
                               hours=4,
                               description='hello world',
                               worklog_system=WorklogSystem.upwork)

        SMonLoader().sync(date.today(), date.today())
        worklogs = Worklog.objects.all().count()
        assert worklogs == 4, worklogs

    def test_linking(self):
        SMonLoader().sync(date.today(), date.today())
        w = Worklog.objects.filter(description='BACK-813').first()

        assert w.issue is not None
        assert w.user_profile is not None

    def tearDown(self):
        [p.stop() for p in self.patchers]


class TestDateUtils(TestCase):
    def test_normalized_dates(self):
        from_date = datetime(2017, 1, 5).date()
        to_date = from_date + timedelta(2)

        dates = list(iterate_dates(from_date, to_date))
        assert dates == [datetime(2017, 1, 5).date(),
                         datetime(2017, 1, 6).date(),
                         datetime(2017, 1, 7).date()], dates

    def test_normalized_dates_reversed(self):
        to_date = datetime(2017, 1, 5).date()
        from_date = to_date + timedelta(2)

        dates = list(iterate_dates(from_date, to_date))
        assert dates == [datetime(2017, 1, 5).date(),
                         datetime(2017, 1, 6).date(),
                         datetime(2017, 1, 7).date()], dates


class TestReportFormatter(TestCase):
    def test_split_by_tickets_rna(self):
        summary = """
        [IOS-111] [[DONE] [REVIEW]] text [IOS-222] daily meeting
        [IOS-333] [DONE]
        [IOS-444] hello world
        [IOS-555] [[DONE]] hello world
        [CUSTOM] hello world
        Additional info"""
        parser = SummaryParser()
        result = parser.parse(summary)

        expected = [['[IOS-111]', ['[DONE]', '[REVIEW]'], 'text'],
                    ['[IOS-222]', [], 'daily meeting'],
                    ['[IOS-333]', ['[DONE]'], ''],
                    ['[IOS-444]', [], 'hello world'],
                    ['[IOS-555]', ['[DONE]'], 'hello world'],
                    ['[CUSTOM]', [], 'hello world\n        Additional info']]
        self.assertEqual(result, expected)
