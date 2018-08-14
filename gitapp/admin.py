from django.contrib import admin

from gitapp.models import GitCommit, GitProject


@admin.register(GitCommit)
class GitCommitAdmin(admin.ModelAdmin):
    list_display = ['short_id', 'branch', 'created_at', 'title', 'additions', 'deletions',
                    'author_profile', 'committer_profile']
    list_filter = ['project', 'author_profile', 'author_email', 'committer_email']
    ordering = ['-created_at']


@admin.register(GitProject)
class GitProjectAdmin(admin.ModelAdmin):
    list_display = ['project_id', 'name', 'hosting']
