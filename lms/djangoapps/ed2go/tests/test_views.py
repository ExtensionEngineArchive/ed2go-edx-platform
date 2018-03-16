import mock
from django.core.urlresolvers import reverse
from django.test import TestCase

from ed2go import constants
from ed2go.tests.mixins import Ed2goTestMixin, SiteMixin


class SSOViewTests(Ed2goTestMixin, SiteMixin, TestCase):
    url = reverse('ed2go.sso')
    domain = 'testserver.fake'

    @mock.patch('ed2go.views.login')
    def test_login(self, mocked_fn):
        """Response redirects to the course page."""
        reg_key = 'dummy-key'
        user = self.create_user()
        course_key = 'course-v1:test+test+test'

        self.create_completion_profile(user=user, course_key=course_key, reg_key=reg_key)

        with mock.patch('ed2go.views.request_valid', return_value=(True, '')):
            response = self.client.post(self.url, data={constants.REGISTRATION_KEY: reg_key})

        expected_url = self.get_full_url(
            reverse('course_root', kwargs={'course_id': course_key})
        )
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)
        self.assertTrue(mocked_fn.called)

    def test_redirect_return_url(self):
        """Redirects to the return URL when request invalid."""
        return_url = 'http://www.example.com'
        with mock.patch('ed2go.views.request_valid', return_value=(False, '')):
            response = self.client.post(self.url, data={constants.RETURN_URL: return_url})
        self.assertRedirects(response, return_url, fetch_redirect_response=False)

    def test_bad_request(self):
        """Returns bad request when request invalid and no return URL is sent."""
        with mock.patch('ed2go.views.request_valid', return_value=(False, '')):
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)
