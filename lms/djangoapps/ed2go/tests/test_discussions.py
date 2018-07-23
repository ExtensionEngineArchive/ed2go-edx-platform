import mock
from django.core.urlresolvers import reverse
from django.test import TestCase

from ed2go import constants
from ed2go.tests.mixins import Ed2goTestMixin, SiteMixin
from ed2go.discussions import get_forum_statistics, _get_stats


class DiscussionsApiTests(Ed2goTestMixin, TestCase):
    
    def setUp(self):
        self.course_id = 'course-v1:edX+DemoX+Demo_Course'
        self.user_id = 7
        self.forum_api_data = {
            'latest_comment_or_thread': {
                'thread': {
                    'title': 'bla bla',
                    'courseware_url': 'https://google.com',
                    'commentable_id': 'test_commentable_id',
                    '_id': '4426'
                }
            },
            'latest_threads_count': 1,
            'latest_comments_count': 2,
            'comments_count': 7,
            'threads_count': 2,
            'user_threads_count': 1,
            'user_comments_count': 3
        }

        self.get_stats_data = self.forum_api_data.copy()

        self.get_stats_data['latest_comment_or_thread']['thread']['courseware_url'] = \
        '/courses/{}/discussion/forum/{}/threads/{}'.format(
            self.course_id,
            self.get_stats_data['latest_comment_or_thread']['thread']['commentable_id'],
            self.get_stats_data['latest_comment_or_thread']['thread']['_id']
        )
        self.get_stats_data['latest_thread'] = self.get_stats_data['latest_comment_or_thread']['thread']
        self.get_stats_data['recent_posts_count'] = \
        int(self.get_stats_data['latest_threads_count']) + int(self.get_stats_data['latest_comments_count'])
        self.get_stats_data['all_posts_count'] = \
        int(self.get_stats_data['comments_count']) + int(self.get_stats_data['threads_count'])

        self.expected_data = {
            'recent_posts': self.get_stats_data['recent_posts_count'],
            'all_posts': self.get_stats_data['all_posts_count'],
            'user_threads_count': self.get_stats_data['user_threads_count'],
            'user_comments_count': self.get_stats_data['user_comments_count'],
            'latest_post': self.get_stats_data['latest_thread']
        }
        super(DiscussionsApiTests, self).setUp()

    def test_get_forum_statistics(self):
        """ Test getting forum statistics """
        with mock.patch('ed2go.discussions._get_stats', return_value = self.get_stats_data):
            self.assertEqual(get_forum_statistics(self.course_id, self.user_id), self.expected_data)

    def test_get_stats(self):
        """ Test getting forum statistics """
        with mock.patch('lms.lib.comment_client.utils.perform_request', return_value = self.forum_api_data):
            self.assertEqual(_get_stats(self.course_id, self.user_id), self.get_stats_data)




