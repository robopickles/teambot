from django.contrib.postgres.fields import ArrayField
from django.db import models

from botapp.enums import get_choices, IssueSystem, ServiceType, WorklogSystem


class UserProfile(models.Model):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=255)
    default = models.BooleanField(default=False)
    user_profiles = models.ManyToManyField(UserProfile)


class Tag(models.Model):
    name = models.CharField(max_length=255, unique=True)
    use_tag = models.BooleanField(default=True)


class ServiceAccount(models.Model):
    """
    Reference for JIRA, Upwork or other users
    """

    uid = models.CharField(max_length=50)
    service_type = models.IntegerField(choices=get_choices(ServiceType))
    user_profile = models.ForeignKey(
        UserProfile, related_name='service_accounts', on_delete=models.CASCADE
    )

    def __str__(self):
        return '{}: {}'.format(ServiceType(self.service_type).name, self.uid)


class Issue(models.Model):
    issue_system = models.IntegerField(default=IssueSystem.jira, choices=get_choices(IssueSystem))

    issue_id = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField(blank=True)

    original_estimate = models.FloatField(null=True, blank=True)
    remaining_estimate = models.FloatField(null=True, blank=True)
    tags = ArrayField(models.CharField(max_length=255), blank=True, default=list)

    class Meta:
        unique_together = ['issue_system', 'issue_id']

    def get_admin_url(self):
        return '/admin/botapp/issue/{}/change/'.format(self.id)

    def __str__(self):
        return '[{}] {}'.format(self.issue_id, self.title)


class Worklog(models.Model):
    uniq_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    work_date = models.DateField()
    user_id = models.CharField(max_length=50)
    user_name = models.CharField(max_length=50)
    hours = models.FloatField(default=0)
    description = models.TextField(blank=True)
    worklog_system = models.IntegerField(choices=get_choices(WorklogSystem))

    from_datetime = models.DateTimeField(null=True, blank=True)
    to_datetime = models.DateTimeField(null=True, blank=True)

    user_profile = models.ForeignKey(UserProfile, null=True, blank=True, on_delete=models.SET_NULL)
    issue = models.ForeignKey(Issue, blank=True, null=True, on_delete=models.SET_NULL)

    def get_shiny_description(self):
        if self.issue:
            return self.issue
        else:
            return self.description

    def __str__(self):
        return '[{}/{}]{}: {}, {}/{}'.format(
            self.id, self.uniq_id, self.user_name, self.description, self.work_date, self.hours
        )
