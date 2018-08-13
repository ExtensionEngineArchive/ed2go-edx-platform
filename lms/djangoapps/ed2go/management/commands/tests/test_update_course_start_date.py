from datetime import datetime

import pytz
from django.test import TestCase
from django.core.management.base import CommandError

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from xmodule.modulestore.django import modulestore

from ed2go.management.commands import update_course_start_date
from ed2go.tests.mixins import Ed2goTestMixin


class CommandTests(Ed2goTestMixin, TestCase):
    command = update_course_start_date.Command()

    def setUp(self):
        user = self.create_user()
        user.is_superuser = True
        user.save()
        self.store = modulestore()

    def assertStartDate(self, course_key, start_date):
        course = self.store.get_course(course_key)
        overview = CourseOverview.get_from_id(course_key)
        self.assertEqual(course.start, start_date)
        self.assertEqual(overview.start, start_date)

    def test_no_args(self):
        """CommandError is raised when no args are passed."""
        with self.assertRaises(CommandError):
            self.command.handle()

    def test_too_many_args(self):
        """CommandError is raised when more than two args are passed."""
        with self.assertRaises(CommandError):
            self.command.handle(1, 2, 3)

    def test_update_one_course(self):
        """Course start date in course and overview objects are updated."""
        course = self.create_course()
        previous_start_date = course.start
        new_start_date = datetime(2018, 1, 1, tzinfo=pytz.utc)

        self.assertNotEqual(previous_start_date, new_start_date)
        self.command.handle('2018-1-1', str(course.id))
        self.assertStartDate(course.id, new_start_date)

    def test_update_all_courses(self):
        """Course start date in all courses are updated."""
        course1 = self.create_course()
        course2 = self.create_course()
        previous_start_date1 = course1.start
        previous_start_date2 = course2.start

        new_start_date = datetime(2018, 1, 1, tzinfo=pytz.utc)
        self.assertNotEqual(previous_start_date1, new_start_date)
        self.assertNotEqual(previous_start_date2, new_start_date)

        self.command.handle('2018-1-1')
        self.assertStartDate(course1.id, new_start_date)
        self.assertStartDate(course2.id, new_start_date)
