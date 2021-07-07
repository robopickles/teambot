from collections import defaultdict
from datetime import date, datetime, timedelta

import plotly.graph_objs as go
import plotly.offline as opy
from dateutil.relativedelta import relativedelta
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django_orm_sugar import Q

from botapp.models import Tag, Team, UserProfile, Worklog
from gitapp.models import GitCommit


def iterate_dates(from_date, to_date):
    start_date = min(from_date, to_date)
    end_date = max(from_date, to_date)

    dt = start_date
    while dt <= end_date:
        yield dt
        dt += timedelta(1)


def normalized_values(from_date, to_date, qs, get_date, get_value):
    d = {}
    for item in qs:
        k = get_date(item)
        d[k] = get_value(item)

    values = []
    for dt in iterate_dates(from_date, to_date):
        values.append(d.get(dt))
    return values


class GroupedWorklog:
    def __init__(self, w):
        self.hours = w.hours
        self.description = w.get_shiny_description()
        self.issue = w.issue

    def add(self, w):
        self.hours += w.hours


class Report:
    def __init__(self, user_profile, from_date, to_date):
        self.user_profile = user_profile
        self.from_date = from_date
        self.to_date = to_date

        self.dates_list = sorted(iterate_dates(self.from_date, self.to_date), reverse=True)
        self.issues_list = []

        self.tracker_worklogs = []
        self.tracker_chart = ''

        self.gitlab_commits = []
        self.gitlab_chart = ''
        self.summary = []

        self.calc_report()

    def calc_report(self):
        self.calc_tracker_stats()
        self.calc_gitlab_stats()

        self.calc_summary()

        self.create_tracker_report()
        self.create_gitlab_report()

    def calc_summary(self):
        for i, date in enumerate(self.dates_list):
            grouped_worklogs = self.get_grouped_worklogs(self.tracker_worklogs[i])
            commits = self.gitlab_commits[i]
            d = {
                'date': date,
                'is_weekend': date.weekday() == 5 or date.weekday() == 6,
                'gitlab_commits': commits,
                'gitlab_text': [c.title for c in commits],
                'gitlab_adds': sum([c.additions or 0 for c in commits]),
                'gitlab_dels': sum([-c.deletions or 0 for c in commits]),
                'tracker_worklogs': self.tracker_worklogs[i],
                'tracker_grouped_worklogs': grouped_worklogs,
                'tracker_text': [w.description for w in grouped_worklogs],
                'tracker_hours': sum([w.hours for w in grouped_worklogs]),
            }
            self.summary.append(d)

    def get_grouped_worklogs(self, worklogs):
        groups = {}
        for w in worklogs:
            text = w.get_shiny_description()
            if text in groups:
                groups[text].add(w)
            else:
                groups[text] = GroupedWorklog(w)
        return sorted(groups.values(), key=lambda w: w.hours, reverse=True)

    def create_tracker_report(self):
        hours = [d['tracker_hours'] for d in self.summary]
        texts = ['<br>'.join(map(str, d['tracker_text'])) for d in self.summary]
        trace1 = go.Bar(x=self.dates_list, y=hours, text=texts, name='hours')

        data = go.Data([trace1])
        layout = go.Layout(
            title='Logged Work Time', xaxis={'range': [self.from_date, self.to_date]}
        )
        figure = go.Figure(data=data, layout=layout)

        self.tracker_chart = opy.plot(
            figure, auto_open=False, output_type='div', include_plotlyjs=False
        )

    def get_commit_name(self, c):
        return '[{}] {}'.format(c.issue.issue_id, c.issue.title) if c.issue else c.title

    def calc_gitlab_stats(self):
        qs = GitCommit.objects.filter(
            Q.created_at.date >= self.from_date,
            Q.created_at.date <= self.to_date,
            (Q.author_profile == self.user_profile) | (Q.committer_profile == self.user_profile),
        )

        commits_dict = {}

        for commit in qs:
            k = commit.created_at.date()
            if commits_dict.get(k) is None:
                commits_dict[k] = [commit]

            else:
                commits_dict[k].append(commit)

        for k in self.dates_list:
            self.gitlab_commits.append(commits_dict.get(k, []))

    def calc_tracker_stats(self):
        qs = (
            Worklog.objects.between(self.from_date, self.to_date)
            .filter(user_profile=self.user_profile)
            .order_by('work_date', 'from_datetime')
        )

        worklog_dict = {}
        for w in qs:
            k = w.work_date
            if worklog_dict.get(k) is None:
                worklog_dict[k] = [w]

            else:
                worklog_dict[k].append(w)

        for k in self.dates_list:
            self.tracker_worklogs.append(worklog_dict.get(k, []))

    def create_gitlab_report(self):
        adds = [d['gitlab_adds'] for d in self.summary]
        dels = [d['gitlab_dels'] for d in self.summary]
        texts = ['<br>'.join(map(str, d['gitlab_text'])) for d in self.summary]

        trace1 = go.Bar(
            x=self.dates_list, y=adds, text=texts, name='Additions', marker={'color': 'green'}
        )
        trace2 = go.Bar(x=self.dates_list, y=dels, name='Deletions')

        data = go.Data([trace1, trace2])
        layout = go.Layout(
            title='Gitlab',
            barmode='relative',
            showlegend=False,
            xaxis={'range': [self.from_date, self.to_date]},
        )
        figure = go.Figure(data=data, layout=layout)
        self.gitlab_chart = opy.plot(
            figure, auto_open=False, output_type='div', include_plotlyjs=False
        )


def get_user_profiles(request):
    if request.user.is_superuser:
        return UserProfile.objects.order_by('name')
    else:
        return Team.objects.filter(default=True).first().user_profiles.all().order_by('name')


class DateRangeForm(forms.Form):
    from_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )
    to_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )
    user = forms.ModelChoiceField(
        queryset=UserProfile.objects.all().order_by('name'),
        widget=forms.Select(attrs={"class": "form-control"}),
    )


@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    template_name = 'dashboard.html'

    def get(self, request):
        data = {
            'from_date': request.GET.get('from_date', date.today() - timedelta(14)),
            'to_date': request.GET.get('to_date', date.today()),
            'user': request.GET.get('user', get_user_profiles(request).first().id),
        }

        form = DateRangeForm(data)
        form.fields['user'].queryset = get_user_profiles(request)

        c = {'form': form}

        if form.is_valid():
            c['reports'] = self.get_reports(
                form.cleaned_data['from_date'],
                form.cleaned_data['to_date'],
                form.cleaned_data['user'],
            )
        return render(request, self.template_name, c)

    def get_reports(self, from_date, to_date, user):
        reports = []

        for u in UserProfile.objects.filter(id=user.id).order_by('name'):
            reports.append(Report(u, from_date, to_date))

        return reports


USE_TAGS = set(
    [
        'backend_maintenance',
        'backend_scaling',
        'batch_upload',
        'body_labeling',
        'client_demo',
        'datawanna',
        'demo',
        'due_diligence',
        'labeler',
        'licensing_P0',
        'metrics',
        'occlusions',
        'public_sdk',
        'q3_not_planned',
        'sdk',
        'studio_maintenance',
        'technical_debt',
    ]
)


@method_decorator(login_required, name='dispatch')
class TagsTimeView(View):
    template_name = 'tags.html'

    def get(self, request):
        use_tags = set(x.name for x in Tag.objects.filter(use_tag=True))
        month = request.GET.get('month')
        if month:
            from_date = datetime.strptime(month, '%Y-%m') - relativedelta(months=1)
        else:
            now = datetime.now()
            from_date = now - relativedelta(day=1, hour=0, minute=0, second=0, microsecond=0)

        logs = Worklog.objects.between(
            from_date, from_date + relativedelta(months=1, days=-1)
        ).prefetch_related('issue', 'user_profile__team_set')
        teams = [x.name for x in Team.objects.all()]
        next_month = (from_date + relativedelta(months=2)).strftime('%Y-%m')
        c = {'teams': teams, 'month': from_date.strftime('%Y-%m'), 'next_month': next_month}

        tags = defaultdict(lambda: {x: 0 for x in teams})
        for log in logs:
            if not log.issue:
                continue

            has_tags = set(log.issue.tags) & use_tags
            if not has_tags:
                continue
            tag = has_tags.pop()
            team = log.user_profile.team_set.first().name
            tags[tag][team] += log.hours

        c['tags'] = {}
        for tag, data in tags.items():
            c['tags'][tag] = [data[x] for x in c['teams']]

        return render(request, self.template_name, c)
