from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator

from ed2go.models import CompletionProfile, CourseSession
from ed2go.utils import extract_course_id_from_url, extract_problem_id

EVENT_BLOCK_MAP = {
    'stop_video': 'video',
    'problem_check': 'problem',
}


def track_user_event(user, event_name, data, page):
    """
    Marks a user's progress in the user's CompletionProfile whenever an
    appropriate event is logged, and sends the report to the third-party API.

    Args:
        user (User): the user object.
        event_name (str): the name of the logged event. Event names are specific to
            edX events and are mapped to the events tracked for the completion report.
        data (str or dict): in the event of a watched video, edX logs data in a dict
            where the `id` key contains the video block ID. For problems this argument
            contains the usage key.
        page (str): URL where the event was triggered. Used to extract the course ID.
    """
    if event_name in EVENT_BLOCK_MAP:
        block_type = EVENT_BLOCK_MAP[event_name]
        course_id = extract_course_id_from_url(page)
        course_key = CourseKey.from_string(course_id)
        if block_type == 'problem':
            data_id = extract_problem_id(data)
        elif block_type == 'video':
            data_id = data['id']

        usage_key = BlockUsageLocator(course_key, block_type, data_id)
        CompletionProfile.mark_progress(user, course_key, usage_key.block_id)


@receiver(user_logged_out)
def logout_handler(sender, user, request, **kwargs):  # pylint: disable=unused-argument
    """Once the user logs out, all active sessions are closed."""
    sessions = CourseSession.objects.filter(user=user, active=True)
    for session in sessions:
        session.close()
