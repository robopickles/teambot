from django.core.management import BaseCommand

from botapp.actions import IssueAction, GitlabScheduledStatusAction
from botapp.management.commands import add_output_arguments


class Command(GitlabScheduledStatusAction, BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('-o', '--output',
                            default='console',
                            choices=['console', 'slack'])
        parser.add_argument('--project-id', required=True, type=int)
        parser.add_argument('--project-url', required=True, type=str)
        add_output_arguments(parser)
