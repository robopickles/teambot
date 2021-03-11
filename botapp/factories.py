import factory
from factory.django import DjangoModelFactory

from .models import ServiceAccount, UserProfile


class UserProfileFactory(DjangoModelFactory):
    active = True

    class Meta:
        model = UserProfile
        django_get_or_create = ('name',)


class ServiceAccountFactory(DjangoModelFactory):
    user_profile = factory.SubFactory(UserProfileFactory)

    class Meta:
        model = ServiceAccount
        django_get_or_create = ('uid', 'service_type', 'user_profile')
