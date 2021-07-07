from datetime import date, timedelta

from django.db.models import F, Sum
from django.template import loader
from django_orm_sugar import Q

from botapp.models import Team, Worklog
from botapp.outputs import get_output
from botapp.trackers import JiraLoader, SMonLoader, UpworkLoader
from gitapp.git_utils import GitlabLoader


class BaseAction:
    def handle(self, *args, **options):
        pass


class BaseDateAction(BaseAction):
    def handle(self, *args, **options):
        today = date.today()
        monday = today - timedelta(today.weekday())
        if options.get('today'):
            from_date = today
            to_date = today

        elif options.get('yesterday'):
            from_date = to_date = today - timedelta(days=1)

        elif options.get('this_week'):
            from_date = monday
            to_date = today

        elif options.get('prev_week'):
            from_date = monday - timedelta(7)
            to_date = monday - timedelta(1)

        elif options.get('last_days'):
            from_date = today - timedelta(days=options.get('last_days') - 1)
            to_date = today
        else:
            from_date = options.get('from_date') or today
            to_date = options.get('to_date') or today

        print('Syncing date range {} to {}'.format(from_date, to_date))
        self.handle_dates(from_date, to_date, options)
        print('Done')

    def handle_dates(self, from_date, to_date, options):
        pass


class IssueAction(BaseDateAction):
    def handle_dates(self, from_date, to_date, options):
        if options.get('sync'):
            UpworkLoader().sync(from_date, to_date)
            SMonLoader().sync(from_date, to_date)

        users = {}
        for w in (
            Worklog.objects.between(from_date, to_date)
            .filter(Q.user_profile.active == True)
            .prefetch_related('user_profile')
        ):
            if w.user_profile and not w.description:
                key = w.user_profile.id
                if key in users:
                    users[key][1] += w.hours
                else:
                    users[key] = [w.user_profile, w.hours]

        if users:
            user_list = sorted(users.values(), key=lambda x: x[0].name)
            t = loader.get_template('missing_memo_report.txt')
            context = {'timesheet': user_list, 'title': options.get('title', '')}

            msg = t.render(context)
            return self.send_message(msg, options)
        else:
            return 'No problems found'

    def send_message(self, msg, options):
        output_name = options.get('output', 'console')
        output = get_output('text', output_name)
        output.send_message(msg, options)
        return msg


class ReportAction(BaseDateAction):
    def handle_dates(self, from_date, to_date, options):
        if options.get('sync', False):
            UpworkLoader().sync(from_date, to_date)
            SMonLoader().sync(from_date, to_date)

        users = []
        team = Team.objects.filter(default=True).first()
        assert team, 'Please specify default team'

        qs = team.user_profiles.all()
        work_date = Q.worklog.work_date
        for u in (
            qs.order_by('name')
            .filter(work_date >= from_date, work_date <= to_date)
            .prefetch_related('worklog_set')
            .annotate(total_hours=Sum(F(Q.worklog.hours.get_path())))
        ):
            users.append(u)
        return self.send_message(users, from_date, to_date, options)

    def send_message(self, users, from_date, to_date, options):
        output_name = options.get('output', 'console')
        output = get_output('report', output_name)
        return output.send_message(users, from_date, to_date, options)


class SyncGitlabAction(BaseDateAction):
    def handle_dates(self, from_date, to_date, options):
        GitlabLoader().sync(from_date, to_date)


class SyncSMonAction(BaseDateAction):
    def handle_dates(self, from_date, to_date, options):
        SMonLoader().sync(from_date, to_date)


class SyncJiraAction(BaseDateAction):
    def handle_dates(self, from_date, to_date, options):
        JiraLoader().sync(from_date, to_date)


class GitlabScheduledStatusAction(BaseAction):
    def handle(self, *args, **options):
        schedules = GitlabLoader().get_pipeline_schedules(options['project_id'])
        self.send_message(schedules, options)

    def send_message(self, schedules, options):
        output_name = options.get('output', 'console')
        output = get_output('schedule_status', output_name)
        return output.send_message(schedules, options)
