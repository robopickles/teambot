import re
from pprint import pprint

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.views import View
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle

from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Frame, Spacer, Image, Table, TableStyle, SimpleDocTemplate
from reportlab.platypus.tables import Table, TableStyle

from agileapp.models import Standup, StandupUserSummary
from botapp.trackers import IssueLoader


def has_perm(permission_name):
    def decorator(method):
        def new_method(self, request, *args, **kwargs):
            if request.user.has_perm(permission_name):
                return method(self, request, *args, **kwargs)
            else:
                return HttpResponseForbidden()

        return new_method
    return decorator


class SummaryParser:
    def chunks(self, l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def parse_modifiers(self, text, modifiers=('DONE', 'REVIEW', 'TEST', 'IN_PROGRESS', 'FIX')):
        modifiers_r = r"(\[(?:{})\])".format('|'.join(modifiers))
        found_modifiers = re.findall(modifiers_r, text, re.IGNORECASE)

        comment = re.sub(modifiers_r, '', text, re.IGNORECASE)
        comment = re.sub(r'\[\W*\]', '', comment)
        return found_modifiers, comment

    def parse(self, source, projects=settings.JIRA_PROJECT_KEYS, custom=('CUSTOM', )):
        """
        Tags like [CUSTOM] don't include digits
        """
        assert projects, 'Jira project prefixes not specified'

        ids = [r'{}-\d+'.format(p) for p in projects] + list(custom)
        project_r = r"(\[(?:{})\])".format('|'.join(ids))
        lines = re.split(project_r, source, maxsplit=0, flags=re.IGNORECASE)
        lines = self.chunks(lines[1:], 2)  # First will be empty string or text before task number

        results = []
        for line in lines:
            modifiers, comment = self.parse_modifiers(line[1])

            results.append([
                line[0],  # Task number
                modifiers,
                comment.strip(),
            ])

        return results


class RenderReport(View):

    @has_perm('agileapp.add_standup')
    def get(self, request, standup_id):
        standup = get_object_or_404(Standup, id=standup_id)
        qs = StandupUserSummary.objects.filter(standup=standup).order_by('user_profile__name')

        return self.gen_pdf_response(request, standup, qs)

    def gen_pdf_response(self, request, standup, summaries):
        style_commands = [
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ]

        response = self.get_empty_pdf_response(request, standup)

        elements = []

        doc = SimpleDocTemplate(response)

        data = []
        for i, s in enumerate(summaries):
            current_row = i * 5
            self.apply_header_style(current_row, style_commands)

            data.extend(self.create_summary_section(s))

        table = Table(data, colWidths=[100, 400])
        table.setStyle(TableStyle(style_commands))

        elements.append(Paragraph("Standup {}".format(standup.date.strftime('%m/%d/%Y')),
                                  ParagraphStyle(name="Normal",
                                                 leftIndent=7,
                                                 spaceAfter=20)))
        elements.append(table)
        doc.build(elements)
        return response

    def apply_header_style(self, current_row, style_commands):
        style_commands.append(('SPAN', (0, current_row), (1, current_row)))
        style_commands.append(('BACKGROUND', (0, current_row), (1, current_row), colors.lightgrey))

    def get_empty_pdf_response(self, request, standup):
        response = HttpResponse(content_type='application/pdf')
        if 'download' in request.GET:
            response['Content-Disposition'] = 'attachment; filename="standup-{}.pdf"'. \
                format(standup.date.strftime('%d-%m-%y'))
        return response

    def reformat_with_jira(self, text):
        p = SummaryParser()
        parsed = p.parse(text)

        result = []
        for ticket, modifiers, description in parsed:
            issue = IssueLoader().get_issue(ticket)
            m = '[{}]'.format(' '.join(modifiers)) if modifiers else ''
            if issue:
                description = issue.title
            result.append('{} {} {}'.format(ticket, m, description))

        formatted_text = '<br />\n'.join(result)
        if formatted_text:
            return formatted_text
        else:
            return text or '-'

    def gen_cell(self, text):
        p = Paragraph(self.reformat_with_jira(text.replace('\r\n', '\n')),
                      ParagraphStyle(name="Normal"))
        return p

    def create_summary_section(self, summary):
        return [[summary.user_profile, ''],
                ['What was done', self.gen_cell(summary.what_was_done)],
                ['The current task', self.gen_cell(summary.current_task)],
                ['The next task', self.gen_cell(summary.next_task)],
                ['General notes', self.gen_cell(summary.general_notes)]]
