import os
from pprint import pprint

from django.template import loader
from slackclient import SlackClient


ALL_OUTPUTS = {}


def register_output(cls):
    key = (cls.message_type, cls.output_name)
    ALL_OUTPUTS[key] = cls
    return cls


@register_output
class BaseTextOutput:
    message_type = 'text'
    output_name = 'none'

    def send_message(self, message, options):
        pass


@register_output
class ConsoleTextOutput(BaseTextOutput):
    output_name = 'console'

    def send_message(self, message, options):
        print(message)


@register_output
class SlackTextOutput(BaseTextOutput):
    output_name = 'slack'

    def send_message(self, message, options):
        client = SlackClient(os.environ['SLACK_TOKEN'])

        client.api_call("chat.postMessage", channel=options['slack_channel'], text=message, as_user=True)
        

@register_output
class BaseReportOutput:
    message_type = 'report'
    output_name = 'none'

    def format_message(self, users, from_date, to_date):
        if users:
            max_name = max(map(lambda x: len(x.name), users))

            formatted = []
            for u in users:
                dots = '.' * (max_name + 3 - len(u.name))
                formatted.append('{}{}{:.1f}h'.format(u.name, dots, u.total_hours))

            t = loader.get_template('timesheet_report.txt')
            context = {'users': formatted,
                       'from_date': from_date,
                       'to_date': to_date}

            msg = t.render(context)
            return msg
        else:
            return 'No worklogs available'

    def send_message(self, users, from_date, to_date, options):
        return self.format_message(users, from_date, to_date)


@register_output
class ConsoleReportOuptut(BaseReportOutput):
    output_name = 'console'

    def send_message(self, users, from_date, to_date, options):
        msg = self.format_message(users, from_date, to_date)
        print(msg)
        return msg
    

@register_output
class SlackReportOutput(BaseReportOutput):
    output_name = 'slack'

    def send_message(self, users, from_date, to_date, options):
        client = SlackClient(os.environ['SLACK_TOKEN'])

        text = self.format_message(users, from_date, to_date)
        markdown = "```{}```".format(text)
        title = "Click for detailed view"
        pretext = "Report from {} to {}".format(from_date, to_date)

        attachments = [
            {
                "fallback": text,
                "pretext": pretext,
                "title": title,
                "title_link": "http://team.gettipsi.com/?from_date={}&to_date={}".format(from_date, to_date),
                "text": markdown,
                "mrkdwn_in": ["text"],
                "color": options.get('slack_color', "#7CD197"),
            }
        ]

        client.api_call("chat.postMessage", channel=options['slack_channel'],
                        attachments=attachments, as_user=True)
        return text


@register_output
class ConsoleSchedulesStatusOutput:
    output_name = 'console'
    message_type = 'schedule_status'

    def send_message(self, schedules, options):
        if schedules:
            s = schedules[0]
            print('-- SCHEDULED TESTS --')
            print('Last run: {}'.format(s['updated_at']))
            print('Status: {}'.format(s['last_pipeline']['status']))


@register_output
class SlackSchedulesStatusOutput:
    output_name = 'slack'
    message_type = 'schedule_status'

    def send_message(self, schedules, options):
        if schedules:
            s = schedules[0]
            client = SlackClient(os.environ['SLACK_TOKEN'])
            last = s.get('last_pipeline')
            if last:
                if last['status'] == 'failed':
                    self.send_slack_message(client, last, 'danger', 'Scheduled tests have failed',
                                            'FAILED', options)
                elif last['status'] == 'success':
                    self.send_slack_message(client, last, 'good',
                                            'Scheduled tests have passed successfully', 'SUCCESS',
                                            options)
                elif last['status'] == 'running':
                    self.send_slack_message(client, last, '#439FE0',
                                            'Scheduled tests are still running', 'RUNNING',
                                            options)

    def send_slack_message(self, client, pipeline, color, title, status, options):
        project_url = options.get('project_url', '')
        attachments = [{
            "fallback": title,
            'title': title,
            "text": "<{project_url}/pipelines/{pipeline_id}|Pipeline #{pipeline_id}>"
                    " - {status}".format(pipeline_id=pipeline['id'], project_url=project_url,
                                         status=status),
            "color": color
        }]
        client.api_call("chat.postMessage", channel=options['slack_channel'], as_user=True,
                        attachments=attachments)


def get_output(message_type, output_name):
    """
    Get registered output
    :param message_type: text or report
    :param output_name: console or slack
    :return: 
    """
    return ALL_OUTPUTS[(message_type, output_name)]()
