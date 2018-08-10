import logging
from datetime import datetime

import pytz
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from opaque_keys.edx.keys import CourseKey

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from xmodule.modulestore.django import modulestore

LOG = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Update the course start date both in the course module store object and the course overview.
    The course overview start date is the one displayed in the course on LMS, but the module
    store one is updated as well to prevent possible inconsistency issues.

    Usage:
    To update a single course:
        python manage.py lms update_course_start_date '2018-12-30' course-v1:test+test+test

    To update all courses:
        python manage.py lms update_course_start_date '2018-12-30'

    Raises:
        CommandError if no arguments are passed, or if more than two arguments are passed.
    """
    args = '<start_date>'

    def update_start_date(self, course, date):
        """
        Update the passed in course object and the CourseOverview.
        """
        year, month, day = date.split('-')
        new_date = datetime(int(year), int(month), int(day), tzinfo=pytz.utc)
        course.start = new_date
        course_overview = CourseOverview.get_from_id(course.id)
        course_overview.start = new_date
        course_overview.save()
        return course

    def handle(self, *args, **options):
        course_key = None

        if not args:
            raise CommandError('Must specify the course start date and optional course key')
        elif len(args) == 1:
            start_date = args[0]
        elif len(args) == 2:
            start_date = args[0]
            course_key = CourseKey.from_string(args[1])
        else:
            raise CommandError('Only two arguments are supported.')

        user = User.objects.filter(is_superuser=True).first()
        module_store = modulestore()

        if course_key:
            course = module_store.get_course(course_key)
            updated_course = self.update_start_date(course, start_date)
            module_store.update_item(updated_course, user.id)
            LOG.info('Updated start date of course %s to %s', course.id, start_date)
        else:
            for course in module_store.get_courses():
                updated_course = self.update_start_date(course, start_date)
                module_store.update_item(updated_course, user.id)
                LOG.info('Updated start date of course %s to %s', course.id, start_date)
