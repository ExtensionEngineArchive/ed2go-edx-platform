import ddt
import factory
import mock
from django.db.models import signals
from django.test import TestCase

from ed2go.tests.mixins import Ed2goTestMixin
from ed2go.track import track_user_event, logout_handler

# Data taken from the edX Demonstration Course
# pylint: disable=line-too-long
PROBLEM_DATA = 'input_a0effb954cca4759994f1ac9e9434bf4_2_1=yellow&input_a0effb954cca4759994f1ac9e9434bf4_3_1=choice_0&input_a0effb954cca4759994f1ac9e9434bf4_4_1%5B%5D=choice_2'
PROBLEM_PAGE = 'http://localhost:18000/courses/course-v1:edX+DemoX+Demo_Course/courseware/interactive_demonstrations/basic_questions/?activate_block_id=block-v1%3AedX%2BDemoX%2BDemo_Course%2Btype%40sequential%2Bblock%40basic_questions'
VIDEO_DATA = {u'code': u'b7xgknqkQk8', u'id': u'0b9e39477cf34507a7a48f74be381fdd', u'currentTime': 194.29904921934508}
VIDEO_PAGE = 'http://localhost:18000/courses/course-v1:edX+DemoX+Demo_Course/courseware/d8a6192ade314473a78242dfeedfbf5b/edx_introduction/?activate_block_id=block-v1%3AedX%2BDemoX%2BDemo_Course%2Btype%40sequential%2Bblock%40edx_introduction'


@ddt.ddt
class TrackTests(Ed2goTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()

    @ddt.data(
        ('problem_check', PROBLEM_DATA, PROBLEM_PAGE),
        ('stop_video', VIDEO_DATA, VIDEO_PAGE)
    )
    @ddt.unpack
    @factory.django.mute_signals(signals.post_save)
    @mock.patch('ed2go.models.CompletionProfile.mark_progress')
    def test_track_user_event(self, event_name, data, page, mocked_fn):
        """Progress marked."""
        track_user_event(self.user, event_name, data, page)
        self.assertTrue(mocked_fn.called)

    @mock.patch('ed2go.models.CompletionProfile.mark_progress')
    def test_track_user_event_skipped(self, mocked_fn):
        """Progress marking skipped because of unsupported event name."""
        track_user_event(self.user, 'invalid_event', None, None)
        self.assertFalse(mocked_fn.called)

    def test_logout_handler(self):
        """Session is closed for user when the logout_handler is called."""
        session = self.create_course_session(user=self.user)
        self.assertTrue(session.active)

        logout_handler(None, self.user, None)
        session.refresh_from_db()
        self.assertFalse(session.active)
