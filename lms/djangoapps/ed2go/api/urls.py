"""Ed2go API URLs."""
from django.conf.urls import include, patterns, url

from ed2go.api import views


urlpatterns = patterns(
    '',
    url(r'action/$', views.ActionView.as_view(), name='action'),
    url(r'course-session/$', views.CourseSessionView.as_view(), name='course-session'),
    url(r'content-viewed/$', views.ContentViewedView.as_view(), name='content-viewed')
)
