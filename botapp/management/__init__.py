import argparse
from datetime import datetime, date, timedelta

from django.core.management import BaseCommand
from botapp.actions import BaseDateAction


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


class BaseDateCommand(BaseDateAction, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--from-date',
                            help="The first report day YYYY-MM-DD ",
                            type=valid_date)
        parser.add_argument('--to-date',
                            help="The last report day YYYY-MM-DD ",
                            type=valid_date)
        parser.add_argument('--today', help="Use the current day as range (default)",
                            action='store_true')
        parser.add_argument('--last-days', help="Use N last days as range",
                            type=int)
        parser.add_argument('--this-week', help="This week range", action='store_true')
        parser.add_argument('--prev-week', help="The previous week range", action='store_true')
        parser.add_argument('--yesterday', help="Use the previous day as range", action='store_true')
