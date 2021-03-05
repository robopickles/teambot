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
![Total Time Spend](https://github.com/Nepherhotep/teambot/blob/master/screenshots/total_time_logged_chart.png)

3. Worklog/Pushes charts per developers
![Worklog/Pushes Chart](https://github.com/Nepherhotep/teambot/blob/master/screenshots/comparison_chart.png)

4. Worklog/Pushes comparison table per developers
![Comparison Table](https://github.com/Nepherhotep/teambot/blob/master/screenshots/comparison_table.png)

5. Alert about empty reports directly into Slack
6. Send worklog reports into Slack
7. Send Gitlab scheduled tests status into Slack
![Scheduled Tests](https://github.com/Nepherhotep/teambot/blob/master/screenshots/scheduled_tests_message.png)


## Integrations
* Upwork
* Screenshot Monitor
* JIRA
* Gitlab
* Slack

## Quick Installation

Generate `JIRA_TOKEN` here: [https://id.atlassian.com/manage/api-tokens](api-tokens)

* Put docker-compose.yml file in directory and fill setup required variables
```yaml
version: "2"

services:
  web:
    image: nepherhotep/teambot

    ports:
      - "80:80"

    environment:
      - PGHOST=postgres
      - PGDATABASE=postgres
      - PGUSER=postgres

      - DJANGO_SECRET_KEY
      - DJANGO_ALLOWED_HOSTS=localhost,yourdomain.com

      - JIRA_BASE_URL=https://yourdomain.atlassian.net
      - JIRA_PROJECT_KEYS=BACK,WEB,IOS,ANDR
      - JIRA_USER
      - JIRA_TOKEN
      - CUSTOM_ETA_FIELD='customfield_10035'

      - UPWORK_COMPANY_ID
      - UPWORK_TEAM_ID

      - KIBANA_URL
      - GITLAB_SCHEDULED_PROJECT_URL

      - HIPCHAT_TOKEN
      - UPWORK_PUBLIC_KEY
      - UPWORK_SECRET_KEY
      - UPWORK_OAUTH_TOKEN
      - UPWORK_OAUTH_TOKEN_SECRET
      - GITLAB_HOST
      - GITLAB_TOKEN
      - SMON_TOKEN

      - SLACK_TOKEN
      - SLACK_TIMESHEET_REPORT_CHANNEL=management
      - SLACK_ISSUES_REPORT_CHANNEL=development

  postgres:
    image: postgres

  redis:
    image: redis

```
* Setup environment variables
* Launch container ```docker-compose up```
* Enter container ```docker exec -it teambot_web_1 /bin/bash```
* Create table schema with command inside container ```python3 manage.py migrate```
* Create super user inside container ```python3 manage.py create```

## Setting Up Teambot

Once the web is live, you need to enter Django admin and setup team. In the following examples,
web is linked to localhost, but you need to replace it with your real domain name

### Create user profiles

Go to that link http://localhost/admin/botapp/userprofile/add/ and populate user names and
service accounts.
![Add User Profile Image](https://github.com/Nepherhotep/teambot/blob/master/screenshots/add_user_profile.png)
Service types are upwork/sreenshot monitor (smon) or gitlab. UID - user id in the given service.

Note: gitlab UID is email user specified in their GIT settings. It's also possible to add 
several gitlab ids, if user pushes from different environments with different emails

### Create default team

At the moment only a single team is used, but it's still required to create the
entity in database, as it keeps references to team members.
![Create Default Team](https://github.com/Nepherhotep/teambot/blob/master/screenshots/create_default_team.png)

### Create manager accounts

Add managers here http://localhost/admin/auth/user/add/ - the users, who will have access to team statistics.
There are two ways kind of permissions can be set for managers:

* Staff + superuser permissions. Those users will see all the data in teambot and dashboard will show all
developers
* Staff + specific permissions (superuser checkbox is unchecked). Those users will only default team statistics
in dashboard, and the admin will display only explicitly allowed chapters.

Note: manager accounts aren't related User Profiles, whose statistics is collected.

### Tips

* The default page is a team dashboard - http://localhost/.
* To view the previous day worklogs per team - open the following link http://localhost/admin/botapp/worklog/?daterange=yesterday
* To view the full task work logs - just click JIRA link in worklogs screen
