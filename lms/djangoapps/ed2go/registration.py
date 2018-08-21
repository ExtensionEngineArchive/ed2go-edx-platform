import json
from dateutil import parser

from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from student.models import UserProfile

from ed2go import constants as c
from ed2go.utils import generate_username, get_registration_data
from ed2go.models import CompletionProfile


def get_or_create_user_completion_profile(registration_key):
    """
    Get or create a user and completion profile.
    Makes a request to the Ed2go GetRegistration endpoint using the provided
    registration key and fetches or creates a new user and completion profile
    based on the information received in the response.

    Args:
        registration_key (str): The registration key

    Returns:
        User and CompletionProfile instance
    """
    try:
        completion_profile = CompletionProfile.objects.get(registration_key=registration_key)
        user = completion_profile.user
    except CompletionProfile.DoesNotExist:
        registration_data = get_registration_data(registration_key)
        student_data = registration_data[c.REG_STUDENT]

        # The reponse from ed2go contains only the course code
        course_key_string = c.COURSE_KEY_TEMPLATE.format(
            code=registration_data[c.REG_COURSE][c.REG_CODE]
        )
        course_key = CourseKey.from_string(course_key_string)

        try:
            user = User.objects.get(email=student_data[c.REG_EMAIL])
            completion_profile, _ = CompletionProfile.objects.get_or_create(
                user=user,
                registration_key=registration_key,
                course_key=course_key
            )
        except User.DoesNotExist:
            user = User.objects.create(
                first_name=student_data[c.REG_FIRST_NAME],
                last_name=student_data[c.REG_LAST_NAME],
                username=generate_username(student_data[c.REG_FIRST_NAME]),
                email=student_data['Email'],
                is_active=True
            )
            UserProfile.objects.create(
                user=user,
                name=student_data[c.REG_FIRST_NAME] + ' ' + student_data[c.REG_LAST_NAME],
                country=student_data[c.REG_COUNTRY],
                year_of_birth=parser.parse(student_data[c.REG_BIRTHDATE]).year,
                meta=json.dumps({
                    'ReturnURL': registration_data[c.REG_RETURN_URL],
                    'StudentKey': registration_data[c.REG_STUDENT][c.REG_STUDENT_KEY]
                })
            )
            completion_profile = CompletionProfile.objects.create(
                user=user,
                registration_key=registration_key,
                course_key=course_key
            )
    return user, completion_profile


def update_registration(registration_key):
    """
    Update the user information:
        * name
        * country
        * year_of_birth
        * ReturnURL
        * StudentKey

    Args:
        registration_key (str): The registration key with which data is fetched
            from the Ed2go endpoint.

    Returns:
        The user who was updated.
    """
    registration_data = get_registration_data(registration_key)
    student_data = registration_data[c.REG_STUDENT]
    user = User.objects.get(email=student_data[c.REG_EMAIL])

    user.first_name = student_data[c.REG_FIRST_NAME]
    user.last_name = student_data[c.REG_LAST_NAME]

    profile = UserProfile.objects.get(user=user)
    profile.name = student_data[c.REG_FIRST_NAME] + ' ' + student_data[c.REG_LAST_NAME]
    profile.country = student_data[c.REG_COUNTRY]
    profile.year_of_birth = parser.parse(student_data[c.REG_BIRTHDATE]).year

    meta = profile.get_meta() if profile.meta else {}
    meta['ReturnURL'] = registration_data[c.REG_RETURN_URL]
    meta['StudentKey'] = registration_data[c.REG_STUDENT][c.REG_STUDENT_KEY]
    profile.set_meta(meta)
    profile.save()

    return user
