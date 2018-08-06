from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.test import RequestFactory

from xmodule.modulestore.django import modulestore
from openedx.features.course_experience.utils import get_course_outline_block_tree


class Command(BaseCommand):
    """
    Create Discussions topics from course chapter names.
    """

    def handle(self, *args, **options):
        fake_request = RequestFactory().get(u'/')
        fake_request.user = User.objects.get(username='staff')
        module_store = modulestore()
        for course in module_store.get_courses():
            course_block_tree = get_course_outline_block_tree(fake_request, str(course.id))
            for chapter in course_block_tree['children']:
                course.discussion_topics[chapter['display_name']] = {u'id': 'i4x-edx-' + chapter['block_id']};
            module_store.update_item(course, fake_request.user.id)
