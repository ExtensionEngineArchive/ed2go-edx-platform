import mock
from django.test import TestCase

from ed2go import constants as c
from ed2go.registration import update_registration
from ed2go.tests.mixins import Ed2goTestMixin

YEAR_OF_BIRTH = 1990
REGISTRATION_KEY = 'reg-key'
REGISTRATION_DATA = {
    c.REG_REFERENCE_ID: 123,
    c.REG_STUDENT: {
        c.REG_FIRST_NAME: 'tester',
        c.REG_LAST_NAME: 'last-name',
        c.REG_EMAIL: 'tester@example.com',
        c.REG_COUNTRY: 'US',
        c.REG_BIRTHDATE: '{}-01-01T08:00:00Z'.format(YEAR_OF_BIRTH),
        c.REG_STUDENT_KEY: '60accf5f-51f1-4a73-8b70-9654a00ce4ab'
    },
    c.REG_COURSE: {
        c.REG_CODE: 'DEV123x+2018_T2'
    },
    c.REG_RETURN_URL: 'www.example.com'
}


class RegistrationTests(Ed2goTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user(email=REGISTRATION_DATA[c.REG_STUDENT][c.REG_EMAIL])
        self.reg_key = 'dummy-key'

    def assert_user_data(self, user, equal=True):
        student_data = REGISTRATION_DATA[c.REG_STUDENT]
        self.assertEqual(
            user.profile.name == student_data[c.REG_FIRST_NAME] + ' ' + student_data[c.REG_LAST_NAME],
            equal
        )
        self.assertEqual(user.profile.country == student_data[c.REG_COUNTRY], equal)
        self.assertEqual(user.profile.year_of_birth == YEAR_OF_BIRTH, equal)

    @mock.patch('ed2go.registration.get_registration_data', mock.Mock(return_value=REGISTRATION_DATA))
    def test_update_registration(self):
        """Existing user profile updated with new data."""
        self.create_completion_profile(reg_key=self.reg_key)
        self.assert_user_data(self.user, equal=False)

        update_registration(self.reg_key)
        self.user.profile.refresh_from_db()
        self.assert_user_data(self.user)
        self.assertEqual(self.user.profile.get_meta()['ReturnURL'], REGISTRATION_DATA[c.REG_RETURN_URL])
        self.assertEqual(
            self.user.profile.get_meta()['StudentKey'], REGISTRATION_DATA[c.REG_STUDENT][c.REG_STUDENT_KEY]
        )

    @mock.patch('ed2go.registration.get_registration_data', mock.Mock(return_value=REGISTRATION_DATA))
    def test_update_reference_id(self):
        """Reference ID of the existing Completion Profile is updated."""
        ref_id = 100
        self.assertNotEqual(ref_id, REGISTRATION_DATA[c.REG_REFERENCE_ID])
        completion_profile = self.create_completion_profile(reg_key=self.reg_key, ref_id=ref_id)
        self.assertEqual(completion_profile.reference_id, ref_id)

        update_registration(self.reg_key)
        completion_profile.refresh_from_db()
        self.assertEqual(completion_profile.reference_id, REGISTRATION_DATA[c.REG_REFERENCE_ID])
