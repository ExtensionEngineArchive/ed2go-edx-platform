"""
FOR TESTING PURPOSES ONLY!
Created CompletionProfiles will NOT include the registration key value.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from opaque_keys.edx.keys import CourseKey

from ed2go.models import CompletionProfile
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview


class Command(BaseCommand):
    """
    Populate the CompletionProfile instances for all users without one.
    """
    args = 'course_id'

    def handle(self, *args, **options):
        course_id = None
        if len(args) == 1:
            course_id = CourseKey.from_string(args[0])

        users_with_profiles = CompletionProfile.objects.all().values_list('user_id', flat=True)
        users_without_profiles = User.objects.exclude(id__in=users_with_profiles)

        course_ids = [course_id] if course_id else (
            overview.id for overview in CourseOverview.get_all_courses()
        )
        for course_key in course_ids:
            for user in users_without_profiles:
                CompletionProfile.objects.create(user=user, course_key=course_key)
