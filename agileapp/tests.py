from pprint import pprint

from django.contrib.auth.models import User, Permission
from django.test import TestCase, Client

# Create your tests here.
from agileapp.models import Standup, StandupUserSummary
from botapp.models import UserProfile, Team


class TestAgileReport(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('john', password='123456', is_staff=True)

        perm = Permission.objects.get(codename='add_standup')
        self.staff.user_permissions.add(perm)

        self.staff_client = Client()
        self.staff_client.login(username='john', password='123456')

        self.john = UserProfile.objects.create(name='John Doe')

        self.team = Team.objects.create()
        self.standup = Standup.objects.create()

        StandupUserSummary.objects.create(standup=self.standup, user_profile=self.john,
                                          what_was_done='Hello', current_task='World')

        self.staff_user = Client()

    def test_auth(self):
        r = self.staff_client.get('/agile/standup-{}.pdf'.format(self.standup.id))

        self.assertEqual(r.status_code, 200)

    def test_forbidden(self):
        r = self.client.get('/agile/standup-{}.pdf'.format(self.standup.id))

        self.assertEqual(r.status_code, 403)


