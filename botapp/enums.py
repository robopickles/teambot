from enum import IntEnum


def get_choices(e):
    return [(x.value, x.name) for x in e]


def get_enum_name(e, value):
    return e(value).name


class ServiceType(IntEnum):
    system = 0  # user id in your internal system
    upwork = 1
    hipchat = 2  # discontinued
    jira = 3
    gitlab = 4
    github = 5
    smon = 6  # screenshot monitor user


class IssueSystem(IntEnum):
    jira = 0
    github = 1


class GitHosting(IntEnum):
    gitlab = 0
    github = 1


class WorklogSystem(IntEnum):
    upwork = 0
    smon = 2  # screenshotmonitor.com
    jira = 3
