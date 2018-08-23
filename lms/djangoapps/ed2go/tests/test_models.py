from datetime import timedelta

import ddt
import factory
import mock
from django.contrib.auth.models import User
from django.db.models import signals
from django.test import TestCase

from student.models import CourseEnrollment

from ed2go import constants as c
from ed2go.exceptions import CompletionProfileAlreadyExists
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
        CompletionProfile's to_report set to True and
        last_activity_at updated when session is updated.
        """
        session = self.create_course_session(user=self.user)
        completion_profile = CompletionProfile.objects.first()
        completion_profile.to_report = False
        completion_profile.save()
        self.assertFalse(completion_profile.to_report)

        tdelta = self.postpone_freeze_time()
        session.update()

        completion_profile.refresh_from_db()
        self.assertEqual(session.last_activity_at, tdelta)
        self.assertTrue(completion_profile.to_report)

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
        self.registration_key = 'dummy-key'
        self.year_of_birth = 1990
        self.registration_data = self.get_mocked_registration_data(
            reg_key=self.registration_key,
            year_of_birth=self.year_of_birth
        )
        self.user = self.create_user(
            email=self.registration_data[c.REG_STUDENT][c.REG_EMAIL]
        )
        self.course = self.create_course()
        self.course_key = self.course.id

    def _create_profile(self, reg_key=None, ref_id=None):
        return self.create_completion_profile(user=self.user, course_key=str(self.course_key), ref_id=ref_id)

    @factory.django.mute_signals(signals.post_save)
    def test_save(self):
        """A new CompletionProfile instance is created and user enrolled."""
        self.assertFalse(
            CourseEnrollment.objects.filter(user=self.user, course_id=self.course_key).exists()
        )
        self._create_profile()
        enrollment = CourseEnrollment.objects.get(user=self.user, course_id=self.course_key)
        self.assertTrue(enrollment.is_active)

    @mock.patch('ed2go.models.get_registration_data')
    def test_update_reference_id(self, mocked_fn):
        """Reference ID field of the completion profile is fetched and updated."""
        reference_id = 100
        new_reference_id = 999
        mocked_fn.return_value = {c.REG_REFERENCE_ID: new_reference_id}

        completion_profile = self._create_profile(ref_id=reference_id)
        self.assertEqual(completion_profile.reference_id, reference_id)

        completion_profile.update_reference_id()
        self.assertEqual(completion_profile.reference_id, new_reference_id)

    @mock.patch('ed2go.models.get_registration_data')
    def test_profile_activation(self, mocked_fn):
        """CompletionProfile and enrollment are active."""
        mocked_fn.return_value = {
            c.REG_REFERENCE_ID: 123
        }
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
        self.assertTrue(mocked_fn.called)

    @mock.patch('ed2go.models.get_registration_data')
    def test_profile_deactivation(self, mocked_fn):
        """CompletionProfile and enrollment are not active."""
        mocked_fn.return_value = {
            c.REG_REFERENCE_ID: 123
        }
        completion_profile = self._create_profile()
        enrollment = CourseEnrollment.objects.get(user=self.user, course_id=self.course_key)
        self.assertTrue(completion_profile.active)
        self.assertTrue(enrollment.is_active)

        completion_profile.deactivate()
        enrollment.refresh_from_db()
        self.assertFalse(completion_profile.active)
        self.assertFalse(enrollment.is_active)
        self.assertTrue(mocked_fn.called)

    def assert_object_count(self, completion_profile_count, user_count):
        self.assertEqual(CompletionProfile.objects.count(), completion_profile_count)
        self.assertEqual(User.objects.count(), user_count)

    def assert_completion_profile(self, completion_profile, user):
        self.assertEqual(completion_profile.user, user)
        self.assertEqual(completion_profile.registration_key, self.registration_key)
        self.assertEqual(str(completion_profile.course_key), c.COURSE_KEY_TEMPLATE.format(
            code=self.registration_data[c.REG_COURSE][c.REG_CODE]
        ))

    @factory.django.mute_signals(signals.post_save)
    @mock.patch('ed2go.models.get_registration_data')
    def test_create_user_completion_profile(self, mocked_fn):
        """Creates new user and completion profile."""
        mocked_fn.return_value = self.registration_data
        self.user.delete()
        self.assert_object_count(completion_profile_count=0, user_count=0)

        completion_profile = CompletionProfile.create_from_key(self.registration_key)
        user = completion_profile.user
        self.assert_completion_profile(completion_profile, user)
        self.assert_object_count(completion_profile_count=1, user_count=1)

        student_data = self.registration_data[c.REG_STUDENT]
        self.assertEqual(user.profile.name, student_data[c.REG_FIRST_NAME] + ' ' + student_data[c.REG_LAST_NAME])
        self.assertEqual(user.profile.country, student_data[c.REG_COUNTRY])
        self.assertEqual(user.profile.year_of_birth, self.year_of_birth)
        self.assertEqual(user.profile.get_meta()['ReturnURL'], self.registration_data[c.REG_RETURN_URL])
        self.assertEqual(
            user.profile.get_meta()['StudentKey'],
            self.registration_data[c.REG_STUDENT][c.REG_STUDENT_KEY]
        )
        self.assertTrue(mocked_fn.called)

    @factory.django.mute_signals(signals.post_save)
    @mock.patch('ed2go.models.get_registration_data')
    def test_create_existing_user(self, mocked_fn):
        """Creates new completion profile with existing user."""
        mocked_fn.return_value = self.registration_data
        self.assert_object_count(completion_profile_count=0, user_count=1)

        completion_profile = CompletionProfile.create_from_key(self.registration_key)
        self.assert_completion_profile(completion_profile, self.user)
        self.assert_object_count(completion_profile_count=1, user_count=1)
        self.assertTrue(mocked_fn.called)

    def test_create_existing_completion_profile(self):
        """Exception is raised when trying to create existing Completion Profile."""
        self.create_completion_profile(reg_key=self.registration_key)
        self.assert_object_count(completion_profile_count=1, user_count=1)

        with self.assertRaises(CompletionProfileAlreadyExists):
            CompletionProfile.create_from_key(self.registration_key)
        self.assert_object_count(completion_profile_count=1, user_count=1)

    @factory.django.mute_signals(signals.post_save)
    @mock.patch('ed2go.models.get_registration_data')
    def test_create_new_completion_profile_from_data(self, mocked_fn):
        self.assert_object_count(completion_profile_count=0, user_count=1)
        completion_profile = CompletionProfile.create_from_data(self.registration_data)

        self.assert_completion_profile(completion_profile, self.user)
        self.assert_object_count(completion_profile_count=1, user_count=1)
        self.assertFalse(mocked_fn.called)

    def test_create_existing_completion_profile_from_data(self):
        """Exception is raised when trying to create existing Completion Profile."""
        self.create_completion_profile(reg_key=self.registration_key)
        self.assert_object_count(completion_profile_count=1, user_count=1)

        with self.assertRaises(CompletionProfileAlreadyExists):
            CompletionProfile.create_from_data(self.registration_data)
        self.assert_object_count(completion_profile_count=1, user_count=1)


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
