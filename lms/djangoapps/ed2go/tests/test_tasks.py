from datetime import timedelta

import ddt
import mock
import requests
from django.test import TestCase
from waffle.testutils import override_switch

from ed2go.constants import ENABLED_ED2GO_COMPLETION_REPORTING
from ed2go.tasks import THRESHOLD, check_course_sessions, send_completion_report
from ed2go.tests.mixins import Ed2goTestMixin

REGISTRATION_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <UpdateCompletionReportResponse xmlns="https://api.ed2go.com">
            <Response>
                <Result>
                    <Success>{success}</Success>
                </Result>
            </Response>
        </UpdateCompletionReportResponse>
    </soap:Body>
</soap:Envelope>
"""


@ddt.ddt
class TaskTests(Ed2goTestMixin, TestCase):
    def test_check_course_sessions(self):
        """Only the expired session is closed."""
        active_session = self.create_course_session()
        expired_session = self.create_course_session()
        expired_session.last_activity_at = expired_session.last_activity_at - (THRESHOLD + timedelta(minutes=5))
        expired_session.save()

        self.assertTrue(expired_session.active)
        self.assertTrue(active_session.active)

        check_course_sessions()
        expired_session.refresh_from_db()
        active_session.refresh_from_db()
        self.assertTrue(active_session.active)
        self.assertFalse(expired_session.active)

    @override_switch(ENABLED_ED2GO_COMPLETION_REPORTING, active=True)
    @mock.patch('ed2go.models.CompletionProfile.report', {})
    def mock_report_request(self, mocked_post, success='true', status_code=200):
        """
        Mock the whole report request flow with different response
        status code and different success message.
        """
        mocked_response = mock.Mock()
        mocked_response.content = REGISTRATION_RESPONSE.format(success=success)
        mocked_response.status_code = status_code
        mocked_post.return_value = mocked_response
        return send_completion_report()

    @mock.patch.object(requests, 'post')
    def test_send_completion_report(self, mocked_post):
        """Successful sent completion report."""
        self.create_completion_profile()
        self.assertTrue(self.mock_report_request(mocked_post))

    @mock.patch.object(requests, 'post')
    @ddt.data(
        (400, 'true'),
        (200, 'false')
    )
    @ddt.unpack
    def test_send_completion_report_failed(self, status_code, success, mocked_post):
        """Completion report sending failed because of non-200 status code or false success message."""
        self.create_completion_profile()
        self.assertFalse(self.mock_report_request(mocked_post, status_code=status_code, success=success))
