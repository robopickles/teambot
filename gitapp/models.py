from django.contrib.auth.models import User
from django.db import models

from botapp.enums import get_choices, GitHosting


class GitProject(models.Model):
    project_id = models.CharField(max_length=50)
    project_url = models.URLField(blank=True)

    name = models.CharField(max_length=50)
    hosting = models.IntegerField(default=GitHosting.gitlab, choices=get_choices(GitHosting))

    def __str__(self):
        return u'{}/{}/{}'.format(self.project_id, self.name, self.hosting)


class GitCommit(models.Model):
    project = models.ForeignKey(GitProject, null=True, blank=True, on_delete=models.CASCADE)
    issue = models.ForeignKey('botapp.Issue', null=True, blank=True, on_delete=models.SET_NULL)
    author_profile = models.ForeignKey(
        'botapp.UserProfile',
        null=True,
        blank=True,
        related_name='created_commits',
        on_delete=models.SET_NULL,
    )
    committer_profile = models.ForeignKey(
        'botapp.UserProfile',
        null=True,
        blank=True,
        related_name='merged_commits',
        on_delete=models.SET_NULL,
    )

    hash = models.CharField(max_length=40, unique=True)
    short_id = models.CharField(max_length=11)
    title = models.TextField()

    author_name = models.CharField(max_length=255, blank=True)
    author_email = models.CharField(max_length=255, blank=True)
    authored_date = models.DateTimeField(null=True, blank=True)

    committer_name = models.CharField(max_length=255, blank=True)
    committer_email = models.CharField(max_length=255, blank=True)
    committed_date = models.DateTimeField(null=True, blank=True)

    # GIT data
    created_at = models.DateTimeField()
    message = models.TextField()

    # Tipsi data
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    additions = models.IntegerField(null=True, blank=True)
    deletions = models.IntegerField(null=True, blank=True)
    total = models.IntegerField(null=True, blank=True)

    branch = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return '{} "{}"'.format(self.short_id, self.title)
