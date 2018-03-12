import uuid

import mock
from factory.fuzzy import FuzzyText
from opaque_keys.edx.keys import CourseKey

from student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from ed2go.models import CompletionProfile, CourseSession


class Ed2goTestMixin(ModuleStoreTestCase):
    @mock.patch('ed2go.models.CompletionProfile._get_problems_videos', mock.Mock(return_value=({}, {})))
    def create_completion_profile(self, user=None, course_key=None, reg_key=None):
        user = user if user else UserFactory()
        course_key = CourseKey.from_string(course_key) if course_key else CourseKey.from_string(
            'course-v1:test+test+{}'.format(FuzzyText(length=5).fuzz())
        )
        reg_key = reg_key if reg_key else str(uuid.uuid4())

        return CompletionProfile.objects.create(
            user=user,
            course_key=course_key,
            registration_key=reg_key
        )

    def create_course_session(self, user=None, course_key=None, reg_key=None, new_profile=True):
        user = user if user else UserFactory()
        course_key = CourseKey.from_string(course_key) if course_key else CourseKey.from_string(
            'course-v1:test+test+{}'.format(FuzzyText(length=5).fuzz())
        )

        if new_profile:
            self.create_completion_profile(user, str(course_key), reg_key)
        return CourseSession.objects.create(user=user, course_key=course_key)
