import hashlib
import re
import urllib
from xml.etree import ElementTree
from dateutil.parser import parse
from random import randint

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.timezone import now

from ed2go import constants


def request_expired(request_data):
    """
    Validate that the expiration date in the request has not passed.

    Args:
        request_data (dict): The data from the request (POST or GET data).

    Returns:
        bool: True if the expiration date has passed, False otherwise.
    """
    expiration_datetime = request_data.get(constants.REQUEST_EXPIRATION_DATETIME)
    expiration_datetime = parse(urllib.unquote(expiration_datetime))
    return now() > expiration_datetime


def checksum_valid(request_data, request_type):
    """
    Validate that the received checksum is correct.

    Args:
        request_data (dict): The data from the request (POST or GET data).
        request_type (str): Type of the request (examples found in the constants).

    Returns:
        bool: True if the received checksum is correct, False otherwise.

    Raises:
        Exception:
            - the checksum in the request cannot be empty
            - the request type needs to be either an SSO or an Action request
            - none of the parameters needed for checksum generation can be empty
    """
    api_key = settings.ED2GO_API_KEY

    checksum = request_data.get(constants.CHECKSUM)
    if checksum is None:
        raise Exception('Checksum cannot be empty.')

    if request_type == constants.SSO_REQUEST:
        checksum_params = constants.SSO_CHECKSUM_PARAMS
    elif request_type == constants.ACTION_REQUEST:
        checksum_params = constants.ACTION_CHECKSUM_PARAMS
    else:
        raise Exception('Request type %s not supported.' % request_type)

    value_list = [api_key]
    for param in checksum_params:
        param_value = request_data.get(param)
        if param_value is None:
            raise Exception('Param %s cannot be empty.' % param)
        value_list.append(urllib.unquote(param_value))

    checksum_string = ''.join(value_list)
    generated_checksum = hashlib.sha1(checksum_string).hexdigest()
    return checksum == generated_checksum


def request_valid(request_data, request_type):
    """
    Validate the recieved request's expiration date and checksum.

    Args:
        request_data (dict): The data from the request (POST or GET data).
        request_type (str): Type of the request (examples found in the constants).

    Returns:
        bool: True if the received request_data is valid, False otherwise.
    """
    if request_expired(request_data):
        return (False, 'Request expired.')
    if not checksum_valid(request_data, request_type):
        return (False, 'Checksum invalid.')
    return (True, '')


def extract_problem_id(string):
    """
    Extract the problem ID from the problem event input string. Example:
        string: 'input_Sample_ChemFormula_Problem_2_1=2'
    from which the problem ID is 'Sample_ChemFormula_Problem'

    Args:
        string (str): string from which the problem ID is extracted.

    Returns:
        The problem ID string.
    """
    result = re.search(r'(?<=^input_)(\w*\d*)(?=_\d_\d=)', string)
    return result.group() if result else None


def extract_course_id_from_url(url):
    """
    Extract the course ID from a URL. Example
        url: 'http://localhost/courses/course-v1:ex+demo+1/courseware/1414ffd08f739b563ab468b7/'
    from which the coures ID is: 'course-v1:ex+demo+1'

    Args:
        url (str): string from which the course ID is extracted.

    Returns:
        The course ID string.
    """
    result = re.search(settings.COURSE_KEY_REGEX, url)
    result = result.group()
    return result.split('/')[-1]


class XMLHandler(object):
    """Ed2go specific XML handler."""
    headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
    soap_wrapper = '<?xml version="1.0" encoding="utf-8"?>' \
        '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' \
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">' \
        '<soap12:Body>' \
        '{inner}' \
        '</soap12:Body>' \
        '</soap12:Envelope>'

    def xml_from_dict(self, data):
        """
        Construct an XML string that would go into the soap_wrapper inner content.

        Args:
            data (dict): Dictionary with the data that is suppose to be compiled into
                XML. The keys of the dictionary are XML element tags, values are values.
                NOTE: The dictionary has to start with ` 'key': {...} `, e.g.:
                    'root': {
                        'tag': 'value',
                        'tag2': 'value2',
                        ...
                    }
                because the root tag needs the `xmlns` attribute.

        Returns:
            XML formatted string from the input data.
        """
        xml = ''
        for k, v in data.items():
            elements = ''
            for sk, sv in v.items():
                elements += '<{key}>{value}</{key}>'.format(key=sk, value=sv)
            xml += '<{key} xmlns="https://api.ed2go.com">{elements}</{key}>'.format(
                key=k, elements=elements
            )
        return xml

    def request_data_from_dict(self, data):
        return self.soap_wrapper.format(inner=self.xml_from_dict(data))

    def request_data_from_xml(self, data):
        return self.soap_wrapper.format(inner=data)

    def clean_tag(self, el):
        """
        Remove the schema prefix.
        Example:
          "{https://api.ed2go.com}NewRegistration" > "NewRegistration"
        """
        return re.sub(r'{[\w\:\/\.]*}', '', el)

    def dict_from_xml(self, elements):
        """
        Construct a dictionary from the XML tree.

        Args:
            elements (list): List of XML elements that are compiled into a dictionary.

        Returns:
            A dictionary with key being the elements tags.
        """
        data = {}
        for el in elements:
            if el.getchildren():
                data[self.clean_tag(el.tag)] = self.dict_from_xml(el.getchildren())
            else:
                data[self.clean_tag(el.tag)] = el.text
        return data

    def _extract_elements_from_xml(self, xml, path):
        """
        Extract XML elements based on the given path.

        Args:
            xml (str): The whole SOAP XML envelope in string format.
            path (str): The XML path to the sequence with the requested elements.
                Example:
                    './soap:Body' \
                    '/a:GetRegistrationResponse' \
                    '/a:RegistrationsResponse' \
                    '/a:Registrations' \
                    '/a:Registration'

        Returns:
            List of sequences found in the passed in XML string.
        """
        tree = ElementTree.fromstring(xml)
        namespace = {
            'soap': 'http://www.w3.org/2003/05/soap-envelope',
            'a': 'https://api.ed2go.com'
        }
        return tree.findall(path, namespace)

    def registration_data_from_xml(self, xml):
        """
        Extract the registration XML elements from the XML tree.

        Args:
            xml (str): XML tree in string format (raw content from the GetRegistration endpoint.)

        Returns:
            A dictionary with all the registration information extracted from dict.
        """
        path = './soap:Body' \
               '/a:GetRegistrationResponse' \
               '/a:RegistrationsResponse' \
               '/a:Registrations' \
               '/a:Registration'
        elements = self._extract_elements_from_xml(xml, path)
        return self.dict_from_xml(elements[0])

    def completion_update_response_data_from_xml(self, xml):
        """
        Extract the completion update response XML elements from the XML tree.

        Args:
            xml (str): XML tree in string format (raw content from the GetRegistration endpoint.)

        Returns:
            A dictionary with all the response information extracted from dict:
                * Result:
                    - Success
                    - Code
                    - Message
        """
        path = './soap:Body' \
               '/a:UpdateCompletionReportResponse' \
               '/a:Response' \
               '/a:Result'
        elements = self._extract_elements_from_xml(xml, path)
        return self.dict_from_xml(elements[0])


def get_registration_data(reg_key):
    """
    Get the registration information from the Ed2go registration endpoint.
    Example of registration data:
        {
        'Status': 'NewRegistration',
        'BillingMonth': None,
        'ReferenceID': '9673060',
        'ReturnURL': 'https://api.ed2go.com/sandbox/OIC/Classroom/ClassroomLogin.aspx?SiteId=208',
        'Student':
        {
            'City': 'Temecula',
            'FirstName': 'Test',
            'LastName': 'Example',
            'PartnerSiteStudentKey': 'xs',
            'Country': 'US',
            'Birthdate': '1970-01-01T08:00:00Z',
            'State': 'CA',
            'PhoneNumber': '999-999-9999',
            'Address': '123 Abc Lane',
            'PostalCode': '92592',
            'StudentKey': '60accf5f-51f1-4a73-8b70-9654a00ce4ab',
            'Email': 'test@example.com'
        },
        'RegistrationDatetimeGMT': '2018-01-23T18:20:59Z',
        'PartnerSite':
        {
            'URL': 'https://api.ed2go.com/sandbox/OIC/Home.aspx?SiteId=208',
            'Name': 'Test 42 (AT Site Name & OAC > Account > Customize > School Name)',
            'PartnerSiteKey': '2c5c3be4-49be-4dfc-a84d-c1e1c7ffea30',
            'Contacts': None
        },
        'Course':
        {
            'ProductCode': 'T9123',
            'Code': 'course-v1:edX+DemoX+Demo_Course',
            'Title': 'edX Test Course 1'
        },
        'AccessExpirationDatetimeGMT': '2018-07-24T06:59:59Z',
        'Suspended': 'false',
        'RegistrationKey': '9f462c2a-334b-418a-8948-5d0be9ed8ab2',
        'Action': 'NewRegistration'
        }

    Args:
        reg_key (str): registration key which is sent to filter the registration data.

    Returns:
        The registration data in form of a dictionary.
    """
    url = settings.ED2GO_REGISTRATION_SERVICE_URL
    api_key = settings.ED2GO_API_KEY
    xmlh = XMLHandler()
    data = {
        'GetRegistration': {
            'APIKey': api_key,
            'RegistrationKey': reg_key
        }
    }
    request_data = xmlh.request_data_from_dict(data)

    response = requests.post(url, data=request_data, headers=xmlh.headers)
    if response.status_code != 200:
        return None
    return xmlh.registration_data_from_xml(response.content)


def generate_username(first_name):
    """Generates a new unique username string."""
    if not User.objects.filter(username=first_name).exists():
        return first_name
    while True:
        username = first_name + str(randint(1000, 9999))
        if not User.objects.filter(username=username).exists():
            return username


def format_timedelta(tdelta):
    """Format a timedelta object to format: day.HH:MM:SS"""
    days = tdelta.days
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return '{days}.{hours}:{minutes}:{seconds}'.format(
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds
    )
