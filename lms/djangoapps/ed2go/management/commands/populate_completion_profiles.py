"""
FOR TESTING PURPOSES ONLY!
Created CompletionProfiles will NOT include the registration key value.
"""
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from opaque_keys.edx.keys import CourseKey

from ed2go.models import CompletionProfile
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

LOG = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Populate the CompletionProfile instances for all users without one.
    """
    args = 'course_id'

    def handle(self, *args, **options):
        course_id = None
        if len(args) == 1:
            course_id = CourseKey.from_string(args[0])

        course_keys = [course_id] if course_id else (
            overview.id for overview in CourseOverview.get_all_courses()
        )

        for course_key in course_keys:
            users_with_profiles = CompletionProfile.objects.filter(course_key=course_key).values_list('user_id', flat=True)
            users_without_profiles = User.objects.exclude(id__in=users_with_profiles)

            for user in users_without_profiles:
                LOG.info('Creating a new Completion Profile for user %s and course %s', user.username, course_key)
                CompletionProfile.objects.create(user=user, course_key=course_key)
