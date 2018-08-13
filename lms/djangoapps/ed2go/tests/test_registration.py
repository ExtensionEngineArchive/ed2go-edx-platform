import factory
import mock
from django.db.models import signals
from django.contrib.auth.models import User
from django.test import TestCase

from ed2go.constants import COURSE_KEY_TEMPLATE
from ed2go.models import CompletionProfile
from ed2go.registration import get_or_create_user_completion_profile, update_registration
from ed2go.tests.mixins import Ed2goTestMixin

YEAR_OF_BIRTH = 1990
REGISTRATION_DATA = {
    'Student': {
        'FirstName': 'tester',
        'LastName': 'last-name',
        'Email': 'tester@example.com',
        'Country': 'US',
        'Birthdate': '{}-01-01T08:00:00Z'.format(YEAR_OF_BIRTH),
        'StudentKey': '60accf5f-51f1-4a73-8b70-9654a00ce4ab'
    },
    'Course': {
        'Code': 'test123'
    },
    'ReturnURL': 'www.example.com'
}


class RegistrationTests(Ed2goTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user(email=REGISTRATION_DATA['Student']['Email'])
        self.reg_key = 'dummy-key'

    def assert_object_count(self, completion_profile_count, user_count):
        self.assertEqual(CompletionProfile.objects.count(), completion_profile_count)
        self.assertEqual(User.objects.count(), user_count)

    def test_get_user_and_profile(self):
        """Correct user and completion profile returned."""
        completion_profile = self.create_completion_profile(user=self.user, reg_key=self.reg_key)
        user, fetched_profile = get_or_create_user_completion_profile(self.reg_key)

        self.assertEqual(user, self.user)
        self.assertEqual(completion_profile, fetched_profile)
        self.assert_object_count(completion_profile_count=1, user_count=1)

    def assert_completion_profile(self, completion_profile, user):
        self.assertEqual(completion_profile.user, user)
        self.assertEqual(completion_profile.registration_key, self.reg_key)
        self.assertEqual(str(completion_profile.course_key), COURSE_KEY_TEMPLATE.format(
            code=REGISTRATION_DATA['Course']['Code']
        ))

    @factory.django.mute_signals(signals.post_save)
    @mock.patch('ed2go.registration.get_registration_data', mock.Mock(return_value=REGISTRATION_DATA))
    def test_get_user_create_profile(self):
        """User returned, new completion profile created."""
        self.assert_object_count(completion_profile_count=0, user_count=1)

        user, completion_profile = get_or_create_user_completion_profile(self.reg_key)
        self.assert_object_count(completion_profile_count=1, user_count=1)
        self.assertEqual(self.user, user)
        self.assert_completion_profile(completion_profile, self.user)

    def assert_user_data(self, user, equal=True):
        student_data = REGISTRATION_DATA['Student']
        self.assertEqual(user.profile.name == student_data['FirstName'] + ' ' + student_data['LastName'], equal)
        self.assertEqual(user.profile.country == student_data['Country'], equal)
        self.assertEqual(user.profile.year_of_birth == YEAR_OF_BIRTH, equal)
        if user.profile.meta:
            self.assertEqual(user.profile.get_meta()['ReturnURL'] == REGISTRATION_DATA['ReturnURL'], equal)
            self.assertEqual(user.profile.get_meta()['StudentKey'] == REGISTRATION_DATA['Student']['StudentKey'], equal)

    @factory.django.mute_signals(signals.post_save)
    @mock.patch('ed2go.registration.get_registration_data', mock.Mock(return_value=REGISTRATION_DATA))
    def test_create_user_and_profile(self):
        """New user and completion profile created."""
        self.user.delete()
        self.assert_object_count(completion_profile_count=0, user_count=0)

        user, completion_profile = get_or_create_user_completion_profile(self.reg_key)
        self.assert_object_count(completion_profile_count=1, user_count=1)
        self.assert_user_data(user)
        self.assert_completion_profile(completion_profile, user)

    @mock.patch('ed2go.registration.get_registration_data', mock.Mock(return_value=REGISTRATION_DATA))
    def test_update_registration(self):
        """Existing user profile updated with new data."""
        self.assert_user_data(self.user, equal=False)

        update_registration(self.reg_key)
        self.user.profile.refresh_from_db()
        self.assert_user_data(self.user)
