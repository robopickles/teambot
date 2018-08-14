from botapp.management import BaseDateCommand
from botapp.trackers import UpworkLoader


class Command(BaseDateCommand):
    help = 'Sync upwork reports into Django db'

    def handle_dates(self, from_date, to_date, options):
        UpworkLoader(self).sync(from_date, to_date)
