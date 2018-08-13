from datetime import timedelta

import ddt
import factory
import mock
from django.db.models import signals
from django.test import TestCase

from student.models import CourseEnrollment

from ed2go.models import CompletionProfile, CourseSession, ChapterProgress
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


class CompletionProfileTests(Ed2goTestMixin, TestCase):

    def setUp(self):
        self.user = self.create_user()
        self.course = self.create_course()
        self.course_key = self.course.id

    def _create_profile(self):
        return self.create_completion_profile(user=self.user, course_key=str(self.course_key))

    @factory.django.mute_signals(signals.post_save)
    def test_save(self):
        """A new CompletionProfile instance is created and user enrolled."""
        self.assertFalse(
            CourseEnrollment.objects.filter(user=self.user, course_id=self.course_key).exists()
        )
        self._create_profile()
        enrollment = CourseEnrollment.objects.get(user=self.user, course_id=self.course_key)
        self.assertTrue(enrollment.is_active)

    def test_profile_activation(self):
        """CompletionProfile and enrollment are active."""
        completion_profile = self._create_profile()
        completion_profile.active = False
        completion_profile.save()

        enrollment = CourseEnrollment.objects.get(user=self.user, course_id=self.course_key)
        enrollment.update_enrollment(is_active=False)

        enrollment.refresh_from_db()
        self.assertFalse(completion_profile.active)
        self.assertFalse(enrollment.is_active)

        completion_profile.activate()
        enrollment.refresh_from_db()
        self.assertTrue(completion_profile.active)
        self.assertTrue(enrollment.is_active)

    def test_profile_deactivation(self):
        """CompletionProfile and enrollment are not active."""
        completion_profile = self._create_profile()
        enrollment = CourseEnrollment.objects.get(user=self.user, course_id=self.course_key)
        self.assertTrue(completion_profile.active)
        self.assertTrue(enrollment.is_active)

        completion_profile.deactivate()
        enrollment.refresh_from_db()
        self.assertFalse(completion_profile.active)
        self.assertFalse(enrollment.is_active)


@ddt.ddt
class ChapterProgressTests(Ed2goTestMixin, TestCase):
    def setUp(self):
        self.unit_1_id = 'unit_1'
        self.subsection_1_id = 'subsection_1'
        self.subsections = {
            self.subsection_1_id: {
                'viewed': False,
                'units': {
                    self.unit_1_id: {
                        'type': ChapterProgress.UNIT_PROBLEM_TYPE,
                        'done': False
                    },
                    'unit_2': {
                        'type': ChapterProgress.UNIT_VIDEO_TYPE,
                        'done': False
                    },
                }
            }
        }
        self.chapter_progress = self.create_chapter_progress(subsections=self.subsections)

    @ddt.data(
        ChapterProgress.UNIT_PROBLEM_TYPE,
        ChapterProgress.UNIT_VIDEO_TYPE
    )
    def test_units(self, unit_type):
        """One unit of each type is in the subsections."""
        units = self.chapter_progress.units(unit_type)
        self.assertEqual(len(units), 1)

    def test_get_unit(self):
        """Correct unit is returned."""
        unit = self.chapter_progress.get_unit(self.unit_1_id)
        unit_1_mock = self.subsections[self.subsection_1_id]['units'][self.unit_1_id]
        self.assertTrue(unit)
        self.assertEqual(unit_1_mock, unit)

    def test_get_invalid_unit(self):
        """None is returned if unit isn't found."""
        unit = self.chapter_progress.get_unit('invalid_unit_id')
        self.assertIsNone(unit)

    def test_progress(self):
        """Correct progress percent is returned."""
        progress = self.chapter_progress.progress
        self.assertEqual(progress, 0)

        no_subsection_cp = self.create_chapter_progress()
        no_subsection_cp.subsections = None
        progress_no_subs = no_subsection_cp.progress
        self.assertEqual(progress_no_subs, 100)

    def _get_user_course_key(self, cp):
        """Return user and course_key attributes from chapter progress."""
        user = cp.completion_profile.user
        course_key = cp.completion_profile.course_key
        return user, course_key

    def mark_subsection_viewed(self):
        """Subsection is marked as viewed."""
        user, course_key = self._get_user_course_key(self.chapter_progress)

        marked = ChapterProgress.mark_subsection_viewed(user, course_key, self.subsection_1_id)
        self.assertTrue(marked)

    def mark_invalid_subsection_viewed(self):
        """Invalid subsection is not marked as viewed."""
        user, course_key = self._get_user_course_key(self.chapter_progress)

        marked = ChapterProgress.mark_subsection_viewed(user, course_key, 'invalid_subsection_id')
        self.assertFalse(marked)
