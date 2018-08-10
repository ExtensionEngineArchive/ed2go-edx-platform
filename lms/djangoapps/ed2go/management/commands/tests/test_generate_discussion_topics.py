import mock
from django.test import TestCase

from xmodule.modulestore.django import modulestore

from ed2go.management.commands import generate_discussion_topics
from ed2go.tests.mixins import Ed2goTestMixin


class CommandTests(Ed2goTestMixin, TestCase):
    command = generate_discussion_topics.Command()

    def setUp(self):
        user = self.create_user()
        user.is_superuser = True
        user.save()
        self.chapter_1_name = 'First Chapter'
        self.store = modulestore()

        self.mocked_course_outline = {
            'children': [{
                'display_name': self.chapter_1_name,
                'block_id': 'chapter_1'
            }]
        }

    def assertNewDiscussionTopic(self, course_key):
        """Assert the new discussion topic has been added to the existing one."""
        course = self.store.get_course(course_key)
        self.assertEqual(len(course.discussion_topics), 2)
        self.assertIn(self.chapter_1_name, course.discussion_topics)

    def prepare_course(self):
        """Create a course new dicussion topic is not in that course."""
        course = self.create_course()
        self.assertEqual(len(course.discussion_topics), 1)
        self.assertNotIn(self.chapter_1_name, course.discussion_topics)
        return course

    @mock.patch('ed2go.management.commands.generate_discussion_topics.get_course_outline_block_tree')
    def test_dicussions_update_single_course(self, mocked_fn):
        """Discussion topics updated for one course."""
        course = self.prepare_course()
        mocked_fn.return_value = self.mocked_course_outline

        self.command.handle(str(course.id))
        self.assertNewDiscussionTopic(course.id)

    @mock.patch('ed2go.management.commands.generate_discussion_topics.get_course_outline_block_tree')
    def test_dicussions_update_all_courses(self, mocked_fn):
        """Discussion topics updated for all course."""
        course1 = self.prepare_course()
        course2 = self.prepare_course()
        mocked_fn.return_value = self.mocked_course_outline

        self.command.handle()
        self.assertNewDiscussionTopic(course1.id)
        self.assertNewDiscussionTopic(course2.id)
