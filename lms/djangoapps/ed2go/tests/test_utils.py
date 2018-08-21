import hashlib
from datetime import timedelta, datetime

import ddt
import mock
import requests
from django.conf import settings
from django.test import TestCase

from ed2go import constants as c
from ed2go.exceptions import InvalidEd2goRequestError
from ed2go.tests.mixins import Ed2goTestMixin
from ed2go.utils import (
    extract_course_id_from_url,
    format_timedelta,
    generate_username,
    get_registration_data,
    checksum_valid,
    extract_problem_id,
    request_expired,
    request_valid
)
from ed2go.xml_handler import XMLHandler


@ddt.ddt
class UtilsTests(Ed2goTestMixin, TestCase):
    request_data_fixture = {
        c.SSO_REQUEST: {
            c.CHECKSUM: '',
            c.REGISTRATION_KEY: 'dummy-key',
            c.REQUEST_EXPIRATION_DATETIME: str(datetime.now()),
            c.RETURN_URL: 'www.example.com'
        },
        c.ACTION_REQUEST: {
            c.CHECKSUM: '',
            c.ACTION: 'dummy-action',
            c.REGISTRATION_KEY: 'dummy-key',
            c.REQUEST_EXPIRATION_DATETIME: str(datetime.now()),
        }
    }

    def test_request_not_expired(self):
        """Returns False if request not expired."""
        time = self.freeze_time()
        request_data = {
            c.REQUEST_EXPIRATION_DATETIME: str(time + timedelta(minutes=10))
        }
        self.assertFalse(request_expired(request_data))

    def test_request_expired(self):
        """Returns True if request expired."""
        time = self.freeze_time()
        request_data = {
            c.REQUEST_EXPIRATION_DATETIME: str(time - timedelta(minutes=10))
        }
        self.assertTrue(request_expired(request_data))

    @ddt.data(
        (c.SSO_REQUEST, c.SSO_CHECKSUM_PARAMS, True),
        (c.ACTION_REQUEST, c.ACTION_CHECKSUM_PARAMS, True),
        (c.ACTION_REQUEST, [], False),
    )
    @ddt.unpack
    def test_checksum_check(self, request_type, checksum_params, expected_bool):
        """Checksum is valid when correct request data is sent."""
        request_data = self.request_data_fixture[request_type].copy()
        checksum_value_list = [request_data[param] for param in checksum_params]
        checksum_value_list.insert(0, settings.ED2GO_API_KEY)

        request_data[c.CHECKSUM] = hashlib.sha1(''.join(checksum_value_list)).hexdigest()

        self.assertEqual(checksum_valid(request_data, request_type), expected_bool)

    def test_checksum_check_missing_exception(self):
        """InvalidEd2goRequestError is raised when a request without checksum is sent."""
        type = c.SSO_REQUEST
        data = self.request_data_fixture[type]
        data.pop(c.CHECKSUM)
        with self.assertRaises(InvalidEd2goRequestError):
            checksum_valid(data, type)

    def test_checksum_invalid_request_type(self):
        """InvalidEd2goRequestError is raised when an invalid request type is sent."""
        data = self.request_data_fixture[c.SSO_REQUEST]
        with self.assertRaises(InvalidEd2goRequestError):
            checksum_valid(data, 'invalid-type')

    def test_checksum_check_empty_param_exception(self):
        """InvalidEd2goRequestError is raised when a param value is missing."""
        request_data = self.request_data_fixture[c.SSO_REQUEST].copy()
        request_data[c.REGISTRATION_KEY] = None

        with self.assertRaises(InvalidEd2goRequestError):
            checksum_valid(request_data, c.SSO_REQUEST)

    @ddt.data(
        (False, True, True),
        (True, True, False),
        (False, False, False),
    )
    @ddt.unpack
    def test_request_valid_fail(self, request_exp, chksum_valid, expected):
        """Request is valid when requirements are fulfilled."""
        with mock.patch('ed2go.utils.request_expired', return_value=request_exp), \
                mock.patch('ed2go.utils.checksum_valid', return_value=chksum_valid):
            valid, _ = request_valid({}, c.SSO_REQUEST)
            self.assertEqual(valid, expected)

    @ddt.data(
        ('input_Sample_ChemFormula_Problem_2_1=2', 'Sample_ChemFormula_Problem'),
        ('input_c8cc8e77-bdca-b37b-f060-2b7c8084e8bc_2_1%5B%5D=choice_0', 'c8cc8e77-bdca-b37b-f060-2b7c8084e8bc'),
        ('invalid_string', None)
    )
    @ddt.unpack
    def test_extract_problem_id(self, string, expected_result):
        """Problem ID is correctly extracted."""
        self.assertEqual(extract_problem_id(string), expected_result)

    @ddt.data(
        ('http://test/course-v1:test+test+test/courseware/', 'course-v1:test+test+test'),
        ('www.example.com', None)
    )
    @ddt.unpack
    def test_extract_course_id_from_url(self, url, expected):
        """Extracts the course ID from the URL."""
        self.assertEqual(extract_course_id_from_url(url), expected)

    def test_generate_username(self):
        """Returns the name if user does not exist."""
        name = 'tester'
        self.assertEqual(generate_username(name), name)

    def test_generate_username_new_username(self):
        """Generates a new username if user exists."""
        name = 'tester'
        num = 1234
        self.create_user(username=name)

        with mock.patch('ed2go.utils.randint', return_value=num):
            self.assertEqual(generate_username(name), ''.join([name, str(num)]))

    def test_format_timedelta(self):
        """Correctly formats the passed in timedelta."""
        days = 1
        hours = 2
        minutes = 3
        seconds = 4

        tdelta = timedelta(
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )
        expected = '{days}.{hours}:{minutes}:{seconds}'.format(
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )

        self.assertEqual(format_timedelta(tdelta), expected)

    def _mock_post_request(self, status_code=200):
        response_mock = mock.Mock()
        response_mock.status_code = status_code
        response_mock.content = ''
        return response_mock

    @mock.patch.object(requests, 'post')
    def test_get_registration_data(self, request_mock):
        expected = 'registration-data'
        request_mock.return_value = self._mock_post_request()
        with mock.patch.object(XMLHandler, 'registration_data_from_xml', mock.Mock(return_value=expected)):
            self.assertEqual(get_registration_data('dummy-reg-key'), expected)

    @mock.patch.object(requests, 'post')
    def test_get_registration_data_bad_request(self, request_mock):
        """If response is a non-200 status code, None should be returned."""
        request_mock.return_value = self._mock_post_request(status_code=400)
        self.assertIsNone(get_registration_data('dummy-reg-key'))
