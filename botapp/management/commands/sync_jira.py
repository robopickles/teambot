from botapp.management import BaseDateCommand
from botapp.trackers import JiraLoader


class Command(BaseDateCommand):
    help = 'Sync JIRA reports into Django db'

    def handle_dates(self, from_date, to_date, options):
        JiraLoader(self).sync(from_date, to_date)
