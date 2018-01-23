from django.conf.urls import include, patterns, url

from ed2go.api import views


urlpatterns = patterns(
    '',
    url(r'course-session/$', views.CourseSessionView.as_view(), name='course-session'),
)
