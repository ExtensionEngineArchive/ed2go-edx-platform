import urlparse
import uuid
from datetime import timedelta

import factory
from django.db.models import signals
from django.test import Client
from django.utils import timezone
from freezegun import freeze_time
from opaque_keys.edx.keys import CourseKey

from student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

from ed2go.models import CompletionProfile, CourseSession, ChapterProgress


class Ed2goTestMixin(SharedModuleStoreTestCase):
    username = 'tester'
    password = 'password'
    email = 'tester@example.com'

    def create_user(self, username=None, password=None, email=None):
        username = username if username else self.username
        password = password if password else self.password
        email = email if email else self.email
        return UserFactory.create(username=username, password=password, email=email)

    def create_course_key(self, org='test', course='test', run=None):
        """Creates a new instance of CourseKey."""
        course_str = 'course-v1:{org}+{course}+{run}'.format(
            org=org,
            course=course,
            run=run if run else factory.fuzzy.FuzzyText(length=5).fuzz()
        )
        return CourseKey.from_string(course_str)

    @factory.django.mute_signals(signals.post_save)
    def create_completion_profile(self, user=None, course_key=None, reg_key=None):
        """Create a new CompletionProfile instance.

        Args:
            user (User): user added to the CompletionProfile instance.
            course_key (str): course key that will be converted to CourseKey instance and added
                to the CompletionProfile instance.
            reg_key (str): registration key added to the CompletionProfile instance.

        Returns:
            CompletionProfile instance.
        """
        user = user if user else self.create_user()
        course_key = CourseKey.from_string(course_key) if course_key else self.create_course_key()
        reg_key = reg_key if reg_key else str(uuid.uuid4())

        return CompletionProfile.objects.create(
            user=user,
            course_key=course_key,
            registration_key=reg_key
        )

    @factory.django.mute_signals(signals.post_save)
    def create_chapter_progress(self, chapter_id='chapter_id', subsections=None):
        """Create a new ChapterProgress instance.

        Args:
            chapter_id (str): chapter_id attribute value.
            subsections (dict): dictionary containing custom subsections.

        Returns:
            ChapterProgresss instance.
        """
        completion_profile = self.create_completion_profile()
        if not subsections:
            subsections = {
                'subsection_1': {
                    'viewed': False,
                    'units': {
                        'unit_1': {
                            'type': ChapterProgress.UNIT_PROBLEM_TYPE,
                            'done': False
                        },
                        'unit_2': {
                            'type': ChapterProgress.UNIT_VIDEO_TYPE,
                            'done': False
                        },
                    }
                }
            }
        chapter_progress = ChapterProgress.objects.create(
            completion_profile=completion_profile,
            chapter_id=chapter_id,
            subsections=subsections
        )

        return chapter_progress

    def create_course_session(self, user=None, course_key=None, reg_key=None, new_profile=True):
        """Create new CourseSession instance.

        Args:
            user (User): user added to the CourseSession instance.
            course_key (str): course key that will be converted to CourseKey instance and added
                to the CourseSession instance.
            reg_key (str): registration key added to the CourseSession instance.
            new_profile (bool): wether a new CompletionProfile instance will be created or
                an existing one is being used.

        Returns:
            CourseSession instance.
        """
        user = user if user else self.create_user()
        course_key = CourseKey.from_string(course_key) if course_key else self.create_course_key()

        if new_profile:
            self.create_completion_profile(user, str(course_key), reg_key)
        return CourseSession.objects.create(user=user, course_key=course_key)

    def freeze_time(self, time=None):
        """Freezes the time in a test.

        Args:
            time (datetime): datetime to which the time will be frozen. If None now() will be used.

        Returns:
            Datetime object which represents the time to which global time has been frozen.
        """
        time = time if time else timezone.now()
        freezer = freeze_time(time)
        freezer.start()
        self.addCleanup(freezer.stop)
        return time

    def postpone_freeze_time(self, minutes=30):
        """Freeze time to a datetime postponed by the number of minutes passed in."""
        tdelta = timezone.now() + timedelta(minutes=minutes)
        self.freeze_time(tdelta)
        return tdelta

    def create_course(self):
        return CourseFactory.create()


class SiteMixin(object):
    domain = 'testserver.fake'

    def setUp(self, *args, **kwargs):
        super(SiteMixin, self).setUp(*args, **kwargs)
        self.client = Client(SERVER_NAME=self.domain)

    def get_full_url(self, path):
        url = 'http://{}'.format(self.domain)
        return urlparse.urljoin(url, path)
