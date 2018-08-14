from botapp.actions import ReportAction
from botapp.management import BaseDateCommand
from botapp.management.commands import add_output_arguments


class Command(ReportAction, BaseDateCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('-s', '--sync',
                            help='Sync upwork reports first',
                            action='store_true')
        parser.add_argument('-o', '--output',
                            default='console',
                            choices=['console', 'slack'])

        add_output_arguments(parser)
