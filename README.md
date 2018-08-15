# Teambot
Teambot - a service to manage distributed teams

## Introduction

If you ever managed a distributed team, you probably saw how hard it could be continuous status
tracking of the next parameters:

* Who is working on what at the moment.
* How much time was spent to a given task.
* How many time a developer worked in the given day or week.
* How many time was reported to time tracker and if any real pushes were performed
during that time.

Usually that information is scattered across different sources in inconvenient format, so
collecting information altogether can be a challenge. The additional challenge is to make
sure developers report real time on the given tasks, and I'm not even talking about the case,
when the reports are altered on purpose - if workers tend to fill reports by the end of
the week, instead of enabling tracker on time, the report will contain just the approximate
numbers recalled behindhand. The main problem with such reports - the simple tasks will
"consume" time from the undervalued ones and the estimation issue will be hidden in the future.
Teambot collects information from different sources (Upwork, ScreenshotMonitor, Gitlab, JIRA)
into a single place and provides access to it in convenient format.

## How it works

1. When developer assigns a task in JIRA, they need to put the task number into description
of the current task in Upwork or Screenshot Monitor trackers. E.g. put text "WEB-123".
2. Teambot will later fetch reported worklogs from Upwork or Screenshot Monitor, and additionally
fetch issue title, description, and the original estimation.
3. Teambot will also fetch commits from gitlab and build comparison table between tracked time
and pushed commits, that is developers have to push code by the end of the day if the task
is not still complete into a separate branch.

So, developers don't have to log work in JIRA anymore, but you can still see who spend time
on what, and how many time in total was spent to the given task (development, code review, testing)

## Features

1. Show work log analytics per a developer or the full team in the given date/week
2. Show total time spent for the given task
3. Worklog/Pushes charts per developers
4. Worklog/Pushes comparison table per developers
5. Alert about empty reports directly into Slack
6. Send worklog reports into Slack
7. Send Gitlab scheduled tests status into Slack


## Integrations
* Upwork
* Screenshot Monitor
* Gitlab
* Slack

## Installation

1. Fork repository
2. Setup environment variables
3. Edit celery_app.py file to configure scheduled tasks
4. Build and run Docker container