import hashlib
import logging
import re
import urllib
from collections import defaultdict
from random import randint

import requests
from dateutil.parser import parse
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.timezone import now

from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory

from ed2go import constants as c
from ed2go.exceptions import InvalidEd2goRequestError
from ed2go.xml_handler import XMLHandler

LOG = logging.getLogger(__name__)


def request_expired(request_data):
    """
    Validate that the expiration date in the request has not passed.

    Args:
        request_data (dict): The data from the request (POST or GET data).

    Returns:
        bool: True if the expiration date has passed, False otherwise.
    """
    expiration_datetime = request_data.get(c.REQUEST_EXPIRATION_DATETIME)
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
        InvalidEd2goRequestError:
            - the checksum in the request cannot be empty
            - the request type needs to be either an SSO or an Action request
            - none of the parameters needed for checksum generation can be empty
    """
    api_key = settings.ED2GO_API_KEY

    checksum = request_data.get(c.CHECKSUM)
    if checksum is None:
        raise InvalidEd2goRequestError('Checksum cannot be empty.')

    if request_type == c.SSO_REQUEST:
        checksum_params = c.SSO_CHECKSUM_PARAMS
    elif request_type == c.ACTION_REQUEST:
        checksum_params = c.ACTION_CHECKSUM_PARAMS
    else:
        raise InvalidEd2goRequestError('Request type %s not supported.' % request_type)

    value_list = [api_key]
    for param in checksum_params:
        param_value = request_data.get(param)
        if param_value is None:
            raise InvalidEd2goRequestError('Param %s cannot be empty.' % param)
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
        LOG.info('Expired action request. Type: %s', request_type)
        return (False, 'Request expired.')
    if not checksum_valid(request_data, request_type):
        LOG.info('Invalid action request checksum. Type: %s', request_type)
        return (False, 'Checksum invalid.')
    return (True, '')


def extract_problem_id(string):
    """
    Extract the problem ID from the problem event input string. Example:
        string: 'input_Sample_ChemFormula_Problem_2_1=2'
    from which the problem ID is 'Sample_ChemFormula_Problem'
    Or:
        string: 'input_c8cc8e77-bdca-b37b-f060-2b7c8084e8bc_2_1%5B%5D=choice_0'
    problem ID: 'c8cc8e77-bdca-b37b-f060-2b7c8084e8bc'

    Args:
        string (str): string from which the problem ID is extracted.

    Returns:
        The problem ID string.
    """
    result = re.search(r'(?<=^input_)([\w\d-]*)(?=_\d_\d)', string)
    return result.group() if result else None


def extract_course_id_from_url(url):
    """
    Extract the course ID from a URL. Example
        url: 'http://localhost/courses/course-v1:ex+demo+1/courseware/1414ffd08f739b563ab468b7/'
    from which the coures ID is: 'course-v1:ex+demo+1'

    Args:
        url (str): string from which the course ID is extracted.

    Returns:
        The course ID string, or None if no course ID was extracted.
    """
    result = re.search(settings.COURSE_KEY_REGEX, url)
    if not result:
        return None
    result = result.group()
    return result.split('/')[-1]


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
        c.REQ_GET_REGISTRATION: {
            c.REQ_API_KEY: api_key,
            c.REG_REGISTRATION_KEY: reg_key
        }
    }
    request_data = xmlh.request_data_from_dict(data)

    response = requests.post(url, data=request_data, headers=xmlh.headers)
    if response.status_code != 200:
        # TODO: Raise custom exception instead
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


def get_graded_chapters(course, student):
    """Extract the graded chapters and grading information from them in a course.

    Args:
        course (Course): The course from which the chapters are extracted.
        student (User): The student whose grading information is extracted.

    Returns:
        A list of graded chapters. Each chapter is a dictionary containing:
            * display_name: Name of the chapter
            * url_name:
            * started: Wether the student attempted any problems in this chapter
            * grade_percent: Percent of chapter assignments finished
            * perc_of_total: Percent of how much of the total grade this chapter weights
            * sections: list of sections (type SubsectionGrade)
            * total_section_type: Dictionary containing total possible grade for each
                grading policy assignment type contained in this chapter
    """
    course_grade = CourseGradeFactory().create(student, course)
    courseware_summary = course_grade.chapter_grades.values()

    graded_chapters = []
    # total number of occurences of different graded assignment types
    total_num_grade_types = defaultdict(int)

    for chapter in courseware_summary:
        if not chapter['display_name'] == 'hidden':
            started = False
            graded_chapter = chapter.copy()
            total_earned, total_possible = 0, 0
            graded_sections = []
            total_section_type = {}

            for section in chapter['sections']:
                if section.graded:
                    started = True if section.graded_total.first_attempted else started
                    total_earned += section.graded_total.earned
                    total_possible += section.graded_total.possible
                    total_section_type[section.format] = total_possible
                    total_num_grade_types[section.format] += total_possible
                    graded_sections.append(section)

            if graded_sections:
                graded_chapter['started'] = started
                graded_chapter['grade_percent'] = int((total_earned / total_possible) * 100) if total_possible else 0
                graded_chapter['sections'] = graded_sections
                graded_chapter['total_section_type'] = total_section_type
                graded_chapters.append(graded_chapter)

    # percentage of grade for single unit of each assignment type
    unit_grade = {}
    for grader in course.grading_policy['GRADER']:
        if total_num_grade_types[grader['type']]:
            unit_grade[grader['type']] = (grader['weight'] * 100) / total_num_grade_types[grader['type']]
        else:
            unit_grade[grader['type']] = 0

    for chapter in graded_chapters:
        perc_of_total = 0
        for k, v in chapter['total_section_type'].items():
            perc_of_total += unit_grade[k] * v
        chapter['perc_of_total'] = round(perc_of_total)

    return graded_chapters
