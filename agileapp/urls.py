from django.conf.urls import url

from agileapp.views import RenderReport


urlpatterns = [
    url(r'standup-(\d+).pdf$', RenderReport.as_view()),
]
