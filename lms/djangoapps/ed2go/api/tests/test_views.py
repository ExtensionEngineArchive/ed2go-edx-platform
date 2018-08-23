import mock
from django.core.urlresolvers import reverse
from django.test import RequestFactory, TestCase
from opaque_keys.edx.keys import CourseKey, UsageKey
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from ed2go import constants as c
from ed2go.api.views import ActionView, CourseSessionView, ContentViewedView
from ed2go.models import CourseSession
from ed2go.tests.mixins import Ed2goTestMixin


class ActionViewTests(Ed2goTestMixin, TestCase):
    url = reverse('ed2go.api:action')

    def setUp(self):
        self.user = self.create_user()

    def _make_request(self, action, reg_key='dummy-key', valid_request=True):
        request = Request(APIRequestFactory().post(
            self.url,
            {c.ACTION: action, c.REGISTRATION_KEY: reg_key}
        ))
        with mock.patch('ed2go.api.views.request_valid', return_value=(valid_request, '')):
            response = ActionView().post(request)
        return response

    @mock.patch('ed2go.api.views.ActionView.update_registration_status_request')
    @mock.patch('ed2go.models.CompletionProfile.create_from_key')
    def test_new_registration(self, create_mock, update_mock):
        """Creating completion profile method is called."""
        completion_profile = self.create_completion_profile(user=self.user)
        create_mock.return_value = completion_profile
        response = self._make_request(c.NEW_REGISTRATION_ACTION)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(create_mock.called)
        self.assertTrue(update_mock.called)
        _, kwargs = update_mock.call_args
        self.assertEqual(kwargs['status'], c.REG_REGISTRATION_PROCESSED_STATUS)

    @mock.patch('ed2go.api.views.ActionView.update_registration_status_request')
    def test_new_registration_rejected(self, update_mock):
        """Request is rejected because of already existing Completion Profile."""
        completion_profile = self.create_completion_profile(user=self.user)
        response = self._make_request(
            c.NEW_REGISTRATION_ACTION,
            reg_key=completion_profile.registration_key
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(update_mock.called)
        _, kwargs = update_mock.call_args
        self.assertEqual(kwargs['status'], c.REG_REGISTRATION_REJECTED_STATUS)

    @mock.patch('ed2go.api.views.ActionView.update_registration_status_request')
    @mock.patch('ed2go.api.views.update_registration')
    def test_update_registration(self, update_reg_mock, update_status_mock):
        """Updating completion profile function is called."""
        completion_profile = self.create_completion_profile(user=self.user)
        update_reg_mock.return_value = completion_profile
        response = self._make_request(c.UPDATE_REGISTRATION_ACTION)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(update_reg_mock.called)
        self.assertTrue(update_status_mock.called)
        _, kwargs = update_status_mock.call_args
        self.assertEqual(kwargs['status'], c.REG_UPDATE_PROCESSED_STATUS)

    @mock.patch('ed2go.api.views.ActionView.update_registration_status_request')
    @mock.patch('ed2go.models.CompletionProfile.deactivate')
    def test_cancel_registration(self, deactivate_mock, update_mock):
        """Deactivates the completion profile."""
        reg_key = 'dummy-key'
        deactivate_mock.return_value = True
        self.create_completion_profile(user=self.user, reg_key=reg_key)

        response = self._make_request(c.CANCEL_REGISTRATION_ACTION, reg_key=reg_key)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(deactivate_mock.called)
        self.assertTrue(update_mock.called)
        _, kwargs = update_mock.call_args
        self.assertEqual(kwargs['status'], c.REG_CANCELLATION_PROCESSED_STATUS)

    def test_cancel_invalid_registration(self):
        """Cancel registration request is rejected because of non-existing registration."""
        response = self._make_request(c.CANCEL_REGISTRATION_ACTION, reg_key='invalid')
        self.assertEqual(response.status_code, 404)

    def test_invalid_action(self):
        """Returns bad request response for invalid action."""
        response = self._make_request('InvalidAction')
        self.assertEqual(response.status_code, 400)

    def test_invalid_request(self):
        """Returns bad request response for invalid request."""
        response = self._make_request('InvalidRequest', valid_request=False)
        self.assertEqual(response.status_code, 400)


class CourseSessionTests(Ed2goTestMixin, TestCase):
    url = reverse('ed2go.api:course-session')

    def setUp(self):
        self.course_key = 'course-v1:test+test+test'
        self.user = self.create_user()

    def _make_request(self):
        request = RequestFactory().post(
            self.url, {'user': self.username, 'course_id': self.course_key}
        )
        with mock.patch('ed2go.models.CourseSession._update_completion_profile'):
            response = CourseSessionView().post(request)
        return response

    def test_create_new(self):
        """Creates new CourseSession object."""
        self.assertEqual(CourseSession.objects.count(), 0)
        now = self.freeze_time()

        response = self._make_request()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(CourseSession.objects.count(), 1)

        session = CourseSession.objects.first()
        course_key = CourseKey.from_string(self.course_key)

        self.assertEqual(session.user, self.user)
        self.assertEqual(session.course_key, course_key)
        self.assertEqual(session.created_at, now)
        self.assertTrue(session.active)

    def test_update(self):
        """Updates existing CourseSession."""
        session = self.create_course_session(user=self.user, course_key=self.course_key)
        tdelta = self.postpone_freeze_time()
        self._make_request()
        session.refresh_from_db()

        self.assertEqual(session.last_activity_at, tdelta)
        self.assertNotEqual(session.created_at, tdelta)
        self.assertTrue(session.active)


class ContentViewedTests(Ed2goTestMixin, TestCase):
    url = reverse('ed2go.api:content-viewed')
    usage_id = UsageKey.from_string('i4x://org.id/course_id/category/block_id')

    def _make_request(self):
        request = RequestFactory().post(
            self.url, {'usage_id': self.usage_id}
        )
        request.user = self.create_user()
        return ContentViewedView().post(request)

    @mock.patch('ed2go.models.ChapterProgress.mark_subsection_viewed')
    def test_successful_post(self, mocked_fn):
        """ChapterProgress is marked as done and status OK is returned."""
        response = self._make_request()
        self.assertEqual(response.status_code, 204)
        self.assertTrue(mocked_fn.called)

    @mock.patch('ed2go.models.ChapterProgress.mark_subsection_viewed')
    def test_not_found_post(self, mocked_fn):
        """ChapterProgress is not marked as done and status NOT FOUND is returned."""
        mocked_fn.return_value = False
        response = self._make_request()
        self.assertEqual(response.status_code, 404)
        self.assertTrue(mocked_fn.called)
