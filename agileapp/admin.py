from django.contrib import admin

# Register your models here.
from django.forms import Textarea

from agileapp.models import Standup, StandupUserSummary


class StandupUserSummaryInline(admin.TabularInline):
    model = StandupUserSummary
    text_area_inputs = ['what_was_done', 'current_task', 'next_task', 'general_notes']

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in self.text_area_inputs:
            kwargs['widget'] = Textarea(attrs={'rows': 4, 'cols': 25})
        return super(StandupUserSummaryInline, self).formfield_for_dbfield(db_field, **kwargs)


@admin.register(Standup)
class StandupAdmin(admin.ModelAdmin):
    inlines = [StandupUserSummaryInline]
    list_display = ['id', 'date', 'records', 'view_pdf_report', 'download_pdf_report']

    def records(self, obj):
        return obj.standupusersummary_set.count()

    def download_pdf_report(self, obj):
        return '<a href="/agile/standup-{}.pdf?download">Download</a>'.format(obj.id)
    download_pdf_report.allow_tags = True

    def view_pdf_report(self, obj):
        return '<a href="/agile/standup-{}.pdf">View</a>'.format(obj.id)
    view_pdf_report.allow_tags = True
