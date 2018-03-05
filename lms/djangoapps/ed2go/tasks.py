import logging
from datetime import timedelta

import requests
from celery import task
from django.conf import settings
from django.utils.timezone import now
from waffle import switch_is_active

from ed2go.constants import ENABLED_ED2GO_COMPLETION_REPORTING
from ed2go.models import CompletionProfile, CourseSession
from ed2go.utils import XMLHandler

LOG = logging.getLogger(__name__)
THRESHOLD = timedelta(seconds=settings.ED2GO_SESSION_INACTIVITY_THRESHOLD)


@task()
def check_course_sessions():
    """
    Periodic task to close any active sessions whose last activity was longer
    than the THRESHOLD.
    """
    qs = CourseSession.objects.filter(active=True)
    for obj in qs:
        if obj.last_activity_at < (now() - THRESHOLD):
            obj.close(offset_delta=THRESHOLD)


@task()
def send_completion_report():
    """
    Periodic task to send completion reports to ed2go.
    """
    if switch_is_active(ENABLED_ED2GO_COMPLETION_REPORTING):
        qs = CompletionProfile.objects.filter(reported=False)
        xmlh = XMLHandler()
        xml_data = []

        for obj in qs:
            report = obj.report
            report['APIKey'] = settings.ED2GO_API_KEY
            xml_data.append(
                xmlh.xml_from_dict({'UpdateCompletionReport': report})
            )

        request_data = xmlh.request_data_from_xml(''.join(xml_data))
        response = requests.post(
            url=settings.ED2GO_REGISTRATION_SERVICE_URL,
            data=request_data,
            headers=xmlh.headers
        )
        if response.status_code == 200:
            response_data = xmlh.completion_update_response_data_from_xml(response.content)
            if response_data['Success'] == 'true':
                LOG.info('Sent batch completion report update.')
                return True
        LOG.error('Failed to send batch completion report update.')
        return False
