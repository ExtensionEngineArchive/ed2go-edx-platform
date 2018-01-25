import logging
from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now
from celery import task

from .models import CourseSession

LOG = logging.getLogger(__name__)
THRESHOLD = timedelta(seconds=settings.ED2GO_SESSION_INACTIVITY_THRESHOLD)


@task()
def check_course_sessions():
    """
    Periodic task to close any active sessions whos last activity was longer
    than the THRESHOLD.
    """
    qs = CourseSession.objects.filter(active=True)
    for obj in qs:
        if obj.last_activity_at < (now() - TRESHOLD):
            obj.close()
