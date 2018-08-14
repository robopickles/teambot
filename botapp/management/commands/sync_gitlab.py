from botapp.management import BaseDateCommand
from botapp.trackers import UpworkLoader
from gitapp.git_utils import GitlabLoader


class Command(BaseDateCommand):
    help = 'Sync upwork reports into Django db'

    def handle_dates(self, from_date, to_date, options):
        GitlabLoader().sync(from_date, to_date)
