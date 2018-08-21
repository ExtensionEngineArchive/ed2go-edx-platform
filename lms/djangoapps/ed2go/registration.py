from dateutil import parser

from django.contrib.auth.models import User
from student.models import UserProfile

from ed2go import constants as c
from ed2go.utils import get_registration_data
from ed2go.models import CompletionProfile


def update_registration(registration_key):
    """
    Update the user information:
        * name
        * country
        * year_of_birth
        * ReturnURL
        * StudentKey

    Update the reference ID in the Completion Profile.

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

    completion_profile = CompletionProfile.objects.get(registration_key=registration_key)
    completion_profile.reference_id = registration_data[c.REG_REFERENCE_ID]
    completion_profile.save()

    return user
