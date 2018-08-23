from django.test import TestCase

from ed2go import constants as c
from ed2go.registration import update_registration
from ed2go.tests.mixins import Ed2goTestMixin


class RegistrationTests(Ed2goTestMixin, TestCase):
    def setUp(self):
        self.registration_key = 'reg-key'
        self.year_of_birth = 1990
        self.registration_data = self.get_mocked_registration_data(
            reg_key=self.registration_key,
            year_of_birth=self.year_of_birth
        )
        self.user = self.create_user(email=self.registration_data[c.REG_STUDENT][c.REG_EMAIL])

    def assert_user_data(self, user, equal=True):
        student_data = self.registration_data[c.REG_STUDENT]
        self.assertEqual(
            user.profile.name == student_data[c.REG_FIRST_NAME] + ' ' + student_data[c.REG_LAST_NAME],
            equal
        )
        self.assertEqual(user.profile.country == student_data[c.REG_COUNTRY], equal)
        self.assertEqual(user.profile.year_of_birth == self.year_of_birth, equal)

    def test_update_registration(self):
        """Existing user profile updated with new data."""
        self.create_completion_profile(reg_key=self.registration_key)
        self.assert_user_data(self.user, equal=False)

        update_registration(self.registration_data)
        self.user.profile.refresh_from_db()
        self.assert_user_data(self.user)
        self.assertEqual(self.user.profile.get_meta()['ReturnURL'], self.registration_data[c.REG_RETURN_URL])
        self.assertEqual(
            self.user.profile.get_meta()['StudentKey'], self.registration_data[c.REG_STUDENT][c.REG_STUDENT_KEY]
        )

    def test_update_reference_id(self):
        """Reference ID of the existing Completion Profile is updated."""
        ref_id = 100
        self.assertNotEqual(ref_id, self.registration_data[c.REG_REFERENCE_ID])
        completion_profile = self.create_completion_profile(reg_key=self.registration_key, ref_id=ref_id)
        self.assertEqual(completion_profile.reference_id, ref_id)

        update_registration(self.registration_data)
        completion_profile.refresh_from_db()
        self.assertEqual(completion_profile.reference_id, self.registration_data[c.REG_REFERENCE_ID])
