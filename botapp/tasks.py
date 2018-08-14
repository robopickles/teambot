import logging

from teambot.celery_app import app
from botapp.actions import SyncGitlabAction, SyncSMonAction, ReportAction, IssueAction, \
    GitlabScheduledStatusAction


@app.task
def send_issues(**options):
    IssueAction().handle(**options)


@app.task
def send_report(**options):
    ReportAction().handle(**options)


@app.task
def sync_gitlab(**options):
    SyncGitlabAction().handle(**options)


@app.task
def sync_smon(**options):
    SyncSMonAction().handle(**options)


@app.task
def send_gitlab_scheduled_status(**options):
    GitlabScheduledStatusAction().handle(**options)


@app.task
def heartbeat(**options):
    logging.debug("Celery beat service is alive")
