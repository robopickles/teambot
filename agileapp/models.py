from __future__ import unicode_literals

from django.db import models


class StandupUserSummary(models.Model):
    user_profile = models.ForeignKey('botapp.UserProfile')
    standup = models.ForeignKey('Standup')
    what_was_done = models.TextField(blank=True)
    current_task = models.TextField(blank=True)
    next_task = models.TextField(blank=True)
    general_notes = models.TextField(blank=True)


class Standup(models.Model):
    updated = models.DateTimeField(auto_now=True)
    date = models.DateField(auto_now_add=True)
