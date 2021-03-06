import pytest


@pytest.fixture(scope='session', autouse=True)
def session_settings(session_settings):
    session_settings.JIRA_PROJECT_KEYS = ['BACK', 'IOS', 'WEB']
    yield session_settings


NOTIFICATION = '''
{
   "timestamp":1614983754173,
   "webhookEvent":"worklog_created",
   "worklog":{
      "self":"https://wannaby.atlassian.net/rest/api/2/issue/12463/worklog/10320",
      "author":{
         "self":"https://wannaby.atlassian.net/rest/api/2/user?accountId=5f6070093242e8006f4a8950",
         "accountId":"5f6070093242e8006f4a8950",
         "avatarUrls":{
            "48x48":"https://avatar-management"
         },
         "displayName":"Kirill Pinchuk",
         "active":true,
         "timeZone":"Europe/Minsk",
         "accountType":"atlassian"
      },
      "updateAuthor":{
         "self":"https://wannaby.atlassian.net/rest/api/2/user?accountId=5f6070093242e8006f4a8950",
         "accountId":"5f6070093242e8006f4a8950",
         "avatarUrls":{
            "48x48":"https://avatar-management",
         },
         "displayName":"Kirill Pinchuk",
         "active":true,
         "timeZone":"Europe/Minsk",
         "accountType":"atlassian"
      },
      "comment":"1m comment",
      "created":"2021-03-06T01:35:54.173+0300",
      "updated":"2021-03-06T01:35:54.173+0300",
      "started":"2021-03-06T01:34:42.910+0300",
      "timeSpent":"1m",
      "timeSpentSeconds":60,
      "id":"10320",
      "issueId":"12463"
   }
}
'''
