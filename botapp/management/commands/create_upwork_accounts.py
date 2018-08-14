from botapp.management import BaseDateCommand
from botapp.trackers import UpworkLoader, AccountCreator


class Command(BaseDateCommand):
    help = 'Create accounts and upwork profiles based on statistics'

    def handle_dates(self, from_date, to_date, options):
        AccountCreator(self).sync(from_date, to_date)
