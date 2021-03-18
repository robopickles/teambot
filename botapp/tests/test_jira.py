import datetime
import json
import re

import pytest
from requests_mock.mocker import Mocker

from fan_tools.python import py_rel_path

from botapp.models import Worklog
from botapp.trackers import JiraLoader


pytestmark = pytest.mark.usefixtures('mock_jira', 'transactional_db')


@pytest.fixture(scope='session')
def session_settings(session_settings):
    session_settings.JIRA_BASE_URL = 'http://example'
    yield session_settings


@pytest.fixture
def mock_jira(requests_mock: Mocker):
    requests_mock.get(
        '/rest/api/latest/worklog/updated?since=1614556800000',
        json=json.loads(py_rel_path('./data/worklogs.json').read_text()),
    )
    requests_mock.post(
        '/rest/api/latest/worklog/list',
        json=json.loads(py_rel_path('./data/list_worklogs.json').read_text()),
    )
    requests_mock.get(
        re.compile('/rest/api/latest/issue/.*'),
        json=json.loads(py_rel_path('./data/jira_issue.json').read_text()),
    )
    pass


@pytest.fixture
def from_to():
    yield datetime.date(2021, 3, 1), datetime.date(2021, 3, 20)


def test_01_parser(from_to):
    jl = JiraLoader()
    jl.sync(*from_to)
    assert Worklog.objects.count() == 8


@pytest.mark.xfail
def test_02_skip_deletion(from_to):
    jl = JiraLoader()
    jl.sync(*from_to)
    assert Worklog.objects.count() == 8
    f = Worklog.objects.order_by('id').first()
    jl.sync(*from_to)
    f.refresh_from_db()
