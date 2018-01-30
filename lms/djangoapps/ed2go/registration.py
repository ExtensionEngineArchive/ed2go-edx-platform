from dateutil import parser

from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment, UserProfile

from ed2go.utils import generate_username, get_registration_data
from ed2go.models import CourseRegistration


def get_or_create_user_registration(registration_key):
    """
    Get or create a user and course registration.
    Makes a request to the Ed2go GetRegistration endpoint using the provided
    registration key and fetches or creates a new user and course registration
    based on the information received in the response.

    Args:
        registration_key (str): The registration key

    Returns:
        User and CourseRegistration
    """
    try:
        course_registration = CourseRegistration.objects.get(registration_key=registration_key)
        user = course_registration.user
    except CourseRegistration.DoesNotExist:
        registration_data = get_registration_data(registration_key)
        student_data = registration_data['Student']
        course_key = CourseKey.from_string(registration_data['Course']['Code'])

        try:
            user = User.objects.get(email=student_data['Email'])
            course_registration, _ = CourseRegistration.objects.get_or_create(
                user=user,
                registration_key=registration_key,
                course_key=course_key
            )
        except User.DoesNotExist:
            user = User.objects.create(
                username=generate_username(student_data['FirstName'], student_data['LastName']),
                email=student_data['Email'],
                is_active=True
            )
            UserProfile.objects.create(
                user=user,
                name=student_data['FirstName'] + ' ' + student_data['LastName'],
                country=student_data['Country'],
                year_of_birth=parser.parse(student_data['Birthdate']).year,
                meta={
                    'ReturnURL': registration_data['ReturnURL']
                }
            )
            course_registration = CourseRegistration.objects.create(
                user=user,
                registration_key=registration_key,
                course_key=course_key
            )
        CourseEnrollment.enroll(user, course_key=course_registration.course_key)
    return user, course_registration


def update_registration(registration_key):
    """
    Update the user information:
        * name
        * country
        * year_of_birth
        * ReturnURL

    Args:
        registration_key (str): The registration key with which data is fetched
            from the Ed2go endpoint.
    """
    registration_data = get_registration_data(registration_key)
    student_data = registration_data['Student']
    user = User.objects.get(email=student_data['Email'])

    profile = UserProfile.objects.get(user=user)
    profile.name = student_data['FirstName'] + ' ' + student_data['LastName']
    profile.country = student_data['Country']
    profile.year_of_birth = parser.parse(student_data['Birthdate']).year
    profile.meta['ReturnURL'] = registration_data['ReturnURL']
    profile.save()
