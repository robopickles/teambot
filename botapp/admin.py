from datetime import date, timedelta

import json

import plotly.offline as opy
import plotly.graph_objs as go

from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.db.models import Count
from django.db.models import Sum
from django.template import loader
from django_orm_sugar import Q

from botapp.enums import ServiceType
from botapp.models import ServiceAccount, UserProfile, Worklog, Issue, Team


@admin.register(ServiceAccount)
class ServiceAccountAdmin(admin.ModelAdmin):
    list_display = ['service_type', 'uid', 'user_profile']
    list_filter = ['service_type', 'user_profile']


class ServiceAccountInline(admin.TabularInline):
    model = ServiceAccount


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'active', 'linked_accounts']
    inlines = [ServiceAccountInline]

    def linked_accounts(self, obj):
        accounts = []
        for account in obj.service_accounts.all():
            accounts.append(ServiceType(account.service_type).name)

        return ', '.join(accounts)


class WeekListFilter(admin.SimpleListFilter):
    title = 'Date Range'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'daterange'

    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('3days', 'Last 3 days'),
            ('this_week', 'Current week'),
            ('prev_week', 'Previous week'),
            ('prev2_week', 'Prev prev week'),
            ('prev3_week', 'Prev prev prev week'),
            ('4weeks', '4 weeks'),
        )

    def queryset(self, request, queryset):
        if self.value():
            today = date.today()
            monday = today - timedelta(today.weekday())
            if self.value() == 'today':
                return queryset.filter(Q.work_date == date.today())

            elif self.value() == 'yesterday':
                return queryset.filter(Q.work_date == date.today() - timedelta(1))

            elif self.value() == '3days':
                return queryset.filter(Q.work_date >= date.today() - timedelta(2))

            if self.value() == 'this_week':
                return queryset.filter(Q.work_date >= monday)

            elif self.value() == 'prev_week':
                return queryset.filter(Q.work_date >= monday - timedelta(7),
                                       Q.work_date < monday)

            elif self.value() == 'prev2_week':
                return queryset.filter(Q.work_date >= monday - timedelta(14),
                                       Q.work_date < monday - timedelta(7))

            elif self.value() == 'prev3_week':
                return queryset.filter(Q.work_date >= monday - timedelta(21),
                                       Q.work_date < monday - timedelta(14))

            elif self.value() == '4weeks':
                return queryset.filter(Q.work_date >= monday - timedelta(21))

            else:
                return queryset
        else:
            return queryset


class UpworkChangeList(ChangeList):
    def get_results(self, *args, **kwargs):
        super(UpworkChangeList, self).get_results(*args, **kwargs)
        q = self.result_list.aggregate(total_hours=Sum('hours'),
                                       issues_count=Count('issue', distinct=True))
        self.total_hours = q['total_hours']
        self.issues_count = q['issues_count']


@admin.register(Worklog)
class WorklogAdmin(admin.ModelAdmin):
    list_display = ['user', 'work_date', 'week_day', 'logged', 'orig_estimate', 'total', 'description',
                    'open_issue', 'issue_title']
    exclude = ['user_id', 'user_name']
    list_filter = [WeekListFilter, 'user_profile']
    search_fields = ['description', 'issue__title']
    ordering = ['-work_date']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        print(db_field)
        if db_field.name == "user_profile":
            kwargs["queryset"] = UserProfile.objects.order_by('name')
        return super(WorklogAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changelist(self, request, **kwargs):
        return UpworkChangeList

    def user(self, obj):
        if obj.user_profile:
            return obj.user_profile
        else:
            return '{}, {}'.format(obj.user_id, obj.user_name)

    def open_issue(self, obj):
        if obj.issue:
            pattern = '<a href="/admin/botapp/issue/{}/" target="_blank">{}</a>'
            return pattern.format(obj.issue.id, obj.issue.issue_id)
        else:
            return ''
    open_issue.allow_tags = True

    def issue_title(self, obj):
        if obj.issue:
            return obj.issue.title
        else:
            return ''

    def orig_estimate(self, obj):
        if obj.issue and obj.issue.original_estimate:
            return '{:.1f}h'.format(obj.issue.original_estimate)

    def week_day(self, obj):
        return obj.work_date.strftime('%A')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(total=Sum('issue__worklog__hours'))
        return qs

    def total(self, obj):
        return '-' if not obj.total else '{:.1f}h'.format(obj.total)

    def logged(self, obj):
        return '{:.1f}h'.format(obj.hours)


class WorklogInline(admin.TabularInline):
    model = Worklog
    fields = ['work_date', 'user_name', 'hours', 'description']
    readonly_fields = ['work_date', 'user_name', 'hours', 'description']
    extra = 0
    ordering = ['work_date']


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['issue_id', 'issue_system', 'title', 'original_estimate', 'description',
                    'open_link']
    readonly_fields = ['issue_id', 'issue_system', 'title', 'description', 'jira_link',
                       'original_estimate', 'total_hours_worked', 'pie_chart']
    search_fields = ['issue_id']
    exclude = ['url']
    inlines = [WorklogInline]

    def open_link(self, obj):
        return '<a href="{}" target="_blank" >Open</a>'.format(obj.url)

    def jira_link(self, obj):
        return '<a href="{url}" target="_blank" >{url}</a>'.format(url=obj.url)

    def total_hours_worked(self, obj):
        qs = obj.worklog_set.all()
        result = qs.aggregate(total_hours=Sum('hours'))
        return result['total_hours'] or 0

    def plotly_chart(self, issue_id, values, labels):
        trace1 = go.Pie(values=values, labels=labels, textinfo='label+value')

        data = go.Data([trace1])
        layout = go.Layout(title=issue_id)
        figure = go.Figure(data=data, layout=layout)
        div = opy.plot(figure, auto_open=False, output_type='div')
        return div

    def pie_chart(self, obj):
        user_dict = {}
        for w in obj.worklog_set.all():
            name = w.user_profile.name if w.user_profile else w.user_name
            if name not in user_dict:
                user_dict[name] = 0
            user_dict[name] += w.hours

        labels = []
        values = []

        for key, value in user_dict.items():
            labels.append(key)
            values.append(round(value, 1))

        if user_dict:
            return self.plotly_chart(obj.issue_id, values, labels)
        else:
            return 'Nothing to show'

    pie_chart.allow_tags = True
    open_link.allow_tags = True
    jira_link.allow_tags = True


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'default', 'team_members']

    def team_members(self, obj):
        return obj.user_profiles.all().count()
