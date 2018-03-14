import hashlib
from datetime import timedelta, datetime
from xml.etree import ElementTree

import ddt
import mock
import requests
from django.conf import settings
from django.test import TestCase

from ed2go import constants
from ed2go.tests.mixins import Ed2goTestMixin
from ed2go.utils import (
    XMLHandler,
    extract_course_id_from_url,
    format_timedelta,
    generate_username,
    get_registration_data,
    checksum_valid,
    extract_problem_id,
    request_expired,
    request_valid
)


@ddt.ddt
class UtilsTests(Ed2goTestMixin, TestCase):
    request_data_fixture = {
        constants.SSO_REQUEST: {
            constants.CHECKSUM: '',
            constants.REGISTRATION_KEY: 'dummy-key',
            constants.REQUEST_EXPIRATION_DATETIME: str(datetime.now()),
            constants.RETURN_URL: 'www.example.com'
        },
        constants.ACTION_REQUEST: {
            constants.CHECKSUM: '',
            constants.ACTION: 'dummy-action',
            constants.REGISTRATION_KEY: 'dummy-key',
            constants.REQUEST_EXPIRATION_DATETIME: str(datetime.now()),
        }
    }

    def test_request_not_expired(self):
        """Returns False if request not expired."""
        time = self.freeze_time()
        request_data = {
            constants.REQUEST_EXPIRATION_DATETIME: str(time + timedelta(minutes=10))
        }
        self.assertFalse(request_expired(request_data))

    def test_request_expired(self):
        """Returns True if request expired."""
        time = self.freeze_time()
        request_data = {
            constants.REQUEST_EXPIRATION_DATETIME: str(time - timedelta(minutes=10))
        }
        self.assertTrue(request_expired(request_data))

    @ddt.data(
        (constants.SSO_REQUEST, constants.SSO_CHECKSUM_PARAMS, True),
        (constants.ACTION_REQUEST, constants.ACTION_CHECKSUM_PARAMS, True),
        (constants.ACTION_REQUEST, [], False),
    )
    @ddt.unpack
    def test_checksum_check(self, request_type, checksum_params, expected_bool):
        """Checksum is valid when correct request data is sent."""
        request_data = self.request_data_fixture[request_type].copy()
        checksum_value_list = [request_data[param] for param in checksum_params]
        checksum_value_list.insert(0, settings.ED2GO_API_KEY)

        request_data[constants.CHECKSUM] = hashlib.sha1(''.join(checksum_value_list)).hexdigest()

        self.assertEqual(checksum_valid(request_data, request_type), expected_bool)

    @ddt.data(
        ({}, constants.SSO_REQUEST),
        ({constants.CHECKSUM: 'dummy-checksum'}, 'invalid-type')
    )
    @ddt.unpack
    def test_checksum__check_missing_exception(self, request_data, request_type):
        """Exception is raised when:
            * a request without checksum is sent
            * an invalid request type is sent
        """
        with self.assertRaises(Exception):
            checksum_valid(request_data, request_type)

    def test_checksum_check_empty_param_exception(self):
        """Exception is raised when a param value is missing."""
        request_data = self.request_data_fixture[constants.SSO_REQUEST].copy()
        request_data[constants.REGISTRATION_KEY] = None

        with self.assertRaises(Exception):
            checksum_valid(request_data, constants.SSO_REQUEST)

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
            valid, _ = request_valid({}, constants.SSO_REQUEST)
            self.assertEqual(valid, expected)

    @ddt.data(
        ('input_Sample_ChemFormula_Problem_2_1=2', 'Sample_ChemFormula_Problem'),
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


class XMLHandlerTests(TestCase):
    def setUp(self):
        self.xmlh = XMLHandler()

    def test_xml_from_dict(self):
        """Correctly convert a dictionary to XML."""
        data = {
            'root': {
                'key': 'value'
            }
        }
        expected = '<root xmlns="https://api.ed2go.com"><key>value</key></root>'
        self.assertEqual(self.xmlh.xml_from_dict(data), expected)

    def test_clean_tag(self):
        """Extracts the element tag."""
        element = '{https://api.ed2go.com}TestElement'
        expected = 'TestElement'
        self.assertEqual(self.xmlh.clean_tag(element), expected)

    def test_dict_from_xml(self):
        """Correctly converts an XML element to a dict."""
        xml_tree = ElementTree.fromstring('<root><key>value</key></root>')
        expected = {'key': 'value'}
        self.assertEqual(self.xmlh.dict_from_xml(xml_tree), expected)

    def test_registration_response_data_from_xml(self):
        """Correctly converts registration request response XML to a dictionary."""
        expected = {'TestUser': 'tester'}
        test_response_xml = '<?xml version="1.0" encoding="utf-8"?>' \
            '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">' \
            '<soap:Body>' \
            '<GetRegistrationResponse xmlns="https://api.ed2go.com">' \
            '<RegistrationsResponse>' \
            '<Registrations>' \
            '<Registration>' \
            '<TestUser>' + expected['TestUser'] + '</TestUser>' \
            '</Registration>' \
            '</Registrations>' \
            '</RegistrationsResponse>' \
            '</GetRegistrationResponse>' \
            '</soap:Body>' \
            '</soap:Envelope>'

        self.assertEqual(self.xmlh.registration_data_from_xml(test_response_xml), expected)

    def test_completion_response_data_from_xml(self):
        """Correctly converts completion report update request response XML to a dictionary."""
        expected = {'Success': 'true'}
        test_response_xml = '<?xml version="1.0" encoding="utf-8"?>' \
            '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">' \
            '<soap:Body>' \
            '<UpdateCompletionReportResponse xmlns="https://api.ed2go.com">' \
            '<Response>' \
            '<Result>' \
            '<Success>' + expected['Success'] + '</Success>' \
            '</Result>' \
            '</Response>' \
            '</UpdateCompletionReportResponse>' \
            '</soap:Body>' \
            '</soap:Envelope>'

        self.assertEqual(self.xmlh.completion_update_response_data_from_xml(test_response_xml), expected)
