from datetime import timedelta

import mock
from django.test import TestCase

from ed2go.models import CompletionProfile, CourseSession
from ed2go.tests.mixins import Ed2goTestMixin


class CourseSessionTests(Ed2goTestMixin, TestCase):

    def setUp(self):
        self.user = self.create_user()
        self.course_key = self.create_course_key()

    def _create_course_session(self, active=True):
        return CourseSession.objects.create(user=self.user, course_key=self.course_key, active=active)

    @mock.patch('ed2go.models.CourseSession._update_completion_profile')
    def test_create(self, mocked_fn):
        """New CourseSession instance is created."""
        self.assertEqual(CourseSession.objects.count(), 0)
        now = self.freeze_time()

        session = self._create_course_session()
        self.assertEqual(CourseSession.objects.count(), 1)
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.course_key, self.course_key)
        self.assertEqual(session.created_at, now)
        self.assertIsNone(session.closed_at)
        self.assertEqual(session.last_activity_at, now)
        self.assertTrue(session.active)
        self.assertTrue(mocked_fn.called)

    @mock.patch('ed2go.models.CourseSession._update_completion_profile')
    def test_closed_on_create(self, _):
        """Previous instance of CourseSession with same user and course closed when new created."""
        session = self._create_course_session()
        self.assertTrue(session.active)
        self.assertIsNone(session.closed_at)

        now = self.freeze_time()
        new_session = self._create_course_session()
        self.assertTrue(new_session.active)

        session.refresh_from_db()
        self.assertFalse(session.active)
        self.assertEqual(session.closed_at, now)

    def test_update(self):
        """
        CompletionProfile's reported set to False and
        last_activity_at updated when session is updated.
        """
        session = self.create_course_session(user=self.user)
        completion_profile = CompletionProfile.objects.first()
        completion_profile.reported = True
        completion_profile.save()
        self.assertTrue(completion_profile.reported)

        tdelta = self.postpone_freeze_time()
        session.update()

        completion_profile.refresh_from_db()
        self.assertEqual(session.last_activity_at, tdelta)
        self.assertFalse(completion_profile.reported)

    @mock.patch('ed2go.models.CourseSession._update_completion_profile')
    def test_not_updated_when_inactive(self, mocked_fn):
        """update() does nothing when CourseSession is inactive."""
        session = self._create_course_session(active=False)
        last_activity_at = session.last_activity_at

        session.update()
        session.refresh_from_db()  # just in case
        self.assertEqual(session.last_activity_at, last_activity_at)
        self.assertEqual(mocked_fn.call_count, 1)  # just when course session was created

    @mock.patch('ed2go.models.CourseSession._update_completion_profile')
    def test_close(self, mocked_fn):
        """Session closed_at defined and _update_completion_profile called when closing session."""
        session = self._create_course_session()
        now = self.freeze_time()
        self.assertNotEqual(session.closed_at, now)
        self.assertTrue(session.active)

        session.close()
        session.refresh_from_db()
        self.assertEqual(session.closed_at, now)
        self.assertFalse(session.active)
        self.assertEqual(mocked_fn.call_count, 2)

    @mock.patch('ed2go.models.CourseSession._update_completion_profile')
    def test_close_offset(self, _):
        """Session closed with time offset subtracted from closed_at."""
        session = self._create_course_session()
        now = self.freeze_time()
        offset = timedelta(minutes=15)

        session.close(offset)
        session.refresh_from_db()
        self.assertEqual(session.closed_at, now - offset)
        self.assertFalse(session.active)

    @mock.patch('ed2go.models.CourseSession._update_completion_profile')
    def test_not_closed_when_inactive(self, mocked_fn):
        """close() does nothing when CourseSessino is inactive."""
        session = self._create_course_session(active=False)
        session.close()
        session.refresh_from_db()

        self.assertIsNone(session.closed_at)
        self.assertEqual(mocked_fn.call_count, 1)  # just when course session was created

    @mock.patch('ed2go.models.CourseSession._update_completion_profile')
    def test_total_time(self, _):
        """Total time is calculated correctly."""
        starting_time = self.freeze_time()

        first_session_duration = timedelta(minutes=10)
        time_between_sessions = timedelta(minutes=30)
        second_session_created_at = starting_time + first_session_duration + time_between_sessions
        second_session_duration = timedelta(minutes=15)

        first_session = self._create_course_session()
        first_session.close()
        first_session.closed_at = starting_time + first_session_duration
        first_session.save()

        second_session = self._create_course_session()
        second_session.created_at = second_session_created_at
        second_session.last_activity_at = second_session_created_at + second_session_duration
        second_session.save()

        total_time = CourseSession.total_time(user=self.user, course_key=self.course_key)
        self.assertEqual(total_time, first_session_duration + second_session_duration)
