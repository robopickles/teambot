import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teambot.settings')

app = Celery('teambot')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, related_name='celery_tasks')
app.conf.beat_schedule = {
    # sync JIRA worklogs
    'sync-jira-hourly': {
        'task': 'botapp.tasks.sync_jira',
        'schedule': crontab(minute=2),
        'kwargs': {'last_days': 1},
    },
    # That worker will fetch screenshot monitor statistics
    'sync-screenshot-monitor-daily': {
        'task': 'botapp.tasks.sync_smon',
        'schedule': crontab(hour=5, minute=0),
        'kwargs': {'last_days': 2},
    },
    # That worker will hourly fetch gitlab events
    'sync-gitlab-hourly': {
        'task': 'botapp.tasks.sync_gitlab',
        'schedule': crontab(hour='*', minute=50),
        'kwargs': {'last_days': 2},
    },
    # It will collect and send to slack a daily report for the previous day
    'daily-timesheet-report': {
        'task': 'botapp.tasks.send_report',
        'schedule': crontab(hour=5, minute=10),
        'kwargs': {
            "slack_channel": os.environ.get('SLACK_TIMESHEET_REPORT_CHANNEL'),
            "yesterday": True,
            "sync": True,
            "output": "slack",
        },
    },
    # It will send a weekly report on Monday for the previous week
    'weekly-timesheet-report': {
        'task': 'botapp.tasks.send_report',
        'schedule': crontab(hour=5, minute=20, day_of_week=1),
        'kwargs': {
            "slack_color": "#a541d1",
            "prev_week": True,
            "sync": True,
            "slack_channel": os.environ.get('SLACK_TIMESHEET_REPORT_CHANNEL'),
            "output": "slack",
        },
    },
    # Check's if any blank reports are reported during last two days
    'hourly-issues-check': {
        'task': 'botapp.tasks.send_issues',
        'schedule': crontab(hour='*', minute=40),
        'kwargs': {
            "slack_color": "#a541d1",
            "last_days": 2,
            "sync": True,
            "slack_channel": os.environ.get('SLACK_ISSUES_REPORT_CHANNEL'),
            "output": "slack",
        },
    },
    # Check's if any blank reports are still remained in previous week worklogs
    'weekly-issues-check': {
        'task': 'botapp.tasks.send_issues',
        'schedule': crontab(hour=5, minute=30, day_of_week=1),
        'kwargs': {
            "slack_color": "#a541d1",
            "prev_week": True,
            "sync": True,
            "slack_channel": os.environ.get('SLACK_ISSUES_REPORT_CHANNEL'),
            "output": "slack",
        },
    },
    # It will report scheduled tests status into a slack command
    'gitlab-scheduled-status': {
        'task': 'botapp.tasks.send_gitlab_scheduled_status',
        'schedule': crontab(hour=7, minute=0),
        'kwargs': {
            "project_id": '60',
            # you need to use your own project URL here
            "project_url": os.environ.get('GITLAB_SCHEDULED_PROJECT_URL'),
            "output": "slack",
            "slack_channel": os.environ.get('SLACK_ISSUES_REPORT_CHANNEL'),
        },
    },
    # Report every minute into logs that teambot is still alive
    'heartbeat': {'task': 'botapp.tasks.heartbeat', 'schedule': crontab(hour='*', minute='*')},
}
