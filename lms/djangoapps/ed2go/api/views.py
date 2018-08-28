import logging

import requests
from django.conf import settings
from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey, UsageKey
from rest_framework.response import Response
from rest_framework.views import APIView

from ed2go import constants as c
from ed2go.exceptions import CompletionProfileAlreadyExists
from ed2go.models import CompletionProfile, CourseSession, ChapterProgress
from ed2go.registration import update_registration
from ed2go.utils import escape_xml_string, get_registration_data, get_request_info, request_valid
from ed2go.xml_handler import XMLHandler

LOG = logging.getLogger(__name__)


class ActionView(APIView):
    def update_registration_status_request(self, reg_key, ref_id, status, note=None):
        """
        Send a registration status update to the RegistrationService API.

        Args:
            reg_key (str) - the registration key
            ref_id (int) - ReferenceID from the action request
            status (str) - one of the possible registration statuses listed in
                           constants.UPDATE_REGISTRATION_STATUSES
            note (str) - optional note
        """
        xmlh = XMLHandler()
        data = {
            c.REQ_UPDATE_REGISTRATION_STATUS: {
                c.REQ_API_KEY: settings.ED2GO_API_KEY,
                c.REG_REGISTRATION_KEY: reg_key,
                c.REG_REFERENCE_ID: ref_id,
                c.REG_REGISTRATION_STATUS: status
            }
        }
        if note:
            data[c.REQ_UPDATE_REGISTRATION_STATUS][c.REQ_NOTE] = escape_xml_string(note)

        request_data = xmlh.request_data_from_dict(data)
        response = requests.post(
            settings.ED2GO_REGISTRATION_SERVICE_URL,
            data=request_data,
            headers=xmlh.headers
        )

        if response.status_code != 200:
            LOG.info(
                '%s request failed with status %d',
                c.REQ_UPDATE_REGISTRATION_STATUS,
                response.status_code
            )
        else:
            response_data = xmlh.get_response_data_from_xml(
                response_name=c.RESP_UPDATE_REGISTRATION_STATUS,
                xml=response.content
            )
            if response_data[c.RESP_SUCCESS] == 'false':
                LOG.error(
                    '%s request failed with message %s',
                    c.REQ_UPDATE_REGISTRATION_STATUS,
                    response_data[c.RESP_MESSAGE]
                )
            else:
                LOG.info('%s request processed!', c.REQ_UPDATE_REGISTRATION_STATUS)

    def handle_broad_exception(self, action, reg_key, ref_id, exception):
        """
        Handles the action request process' catch-all exception(s) by logging the exception
        and sending an appropriate rejection status update to ed2go.

        Args:
            action (str): Name of the action
            reg_key (str): Registration key of the processed registration
            ref_id (int): Reference ID of the registration status
            exception (Exception): The caught exception

        Returns:
            The appropriate message explaining the exception.
        """
        msg = 'An error happened trying to process the {action} action request [{reg_key}]'.format(
            action=action,
            reg_key=reg_key
        )
        LOG.exception(msg)

        if action == c.NEW_REGISTRATION_ACTION:
            status = c.REG_REGISTRATION_REJECTED_STATUS
        elif action == c.UPDATE_REGISTRATION_ACTION:
            status = c.REG_UPDATE_REJECTED_STATUS
        elif action == c.CANCEL_REGISTRATION_ACTION:
            status = c.REG_CANCELLATION_REJECTED_STATUS
        else:
            raise Exception('Unsupported action {action}'.format(action=action))

        self.update_registration_status_request(
            reg_key=reg_key,
            ref_id=ref_id,
            status=status,
            note='{msg}: {err}'.format(msg=msg, err=exception.message)
        )
        return msg

    def new_registration_action_handler(self, registration_data):
        """
        Handles the NewRegistration action requests.
        Creates a new CompletionProfile based on the data fetched from ed2go API
        via the passed in registration_key value.

        Args:
            registration_data (dict): The fetched registration data.

        Returns:
            - response message
            - response status code - 201 if created, 400 if profile already exists
        """
        registration_key = registration_data[c.REG_REGISTRATION_KEY]
        reference_id = registration_data[c.REG_REFERENCE_ID]

        try:
            completion_profile = CompletionProfile.create_from_data(registration_data)
        except CompletionProfileAlreadyExists:
            msg = 'Completion Profile already exists for registration key {reg_key}'.format(
                reg_key=registration_key
            )
            LOG.error(msg)
            self.update_registration_status_request(
                reg_key=registration_key,
                ref_id=reference_id,
                status=c.REG_REGISTRATION_REJECTED_STATUS,
                note='Registration already exists in the system'
            )
            return msg, 400
        except Exception as e:  # pylint: disable=broad-except
            msg = self.handle_broad_exception(c.NEW_REGISTRATION_ACTION, registration_key, reference_id, e)
            return msg, 400

        msg = 'Completion Profile created for user {user} and course {course}.'.format(
            user=completion_profile.user.username,
            course=completion_profile.course_key
        )
        LOG.info(msg)
        self.update_registration_status_request(
            reg_key=registration_key,
            ref_id=completion_profile.reference_id,
            status=c.REG_REGISTRATION_PROCESSED_STATUS
        )
        return msg, 201

    def update_registration_action_handler(self, registration_data):
        """
        Handles the UpdateRegistration action requests.
        Updates the user information based on the data fetched from ed2go API
        via the passed in registration_key value.

        Args:
            registration_data (dict): The fetched registration data.

        Returns:
            - response message
            - response status code - 200 for successful update
        """
        registration_key = registration_data[c.REG_REGISTRATION_KEY]
        reference_id = registration_data[c.REG_REFERENCE_ID]

        try:
            completion_profile = update_registration(registration_data)
            msg = 'User {user} information updated.'.format(user=completion_profile.user.username)
            LOG.info(msg)
            self.update_registration_status_request(
                reg_key=registration_key,
                ref_id=reference_id,
                status=c.REG_UPDATE_PROCESSED_STATUS
            )
            return msg, 200
        except Exception as e:  # pylint: disable=broad-except
            msg = self.handle_broad_exception(c.UPDATE_REGISTRATION_ACTION, registration_key, reference_id, e)
            return msg, 400

    def cancel_registration_action_handler(self, registration_data):
        """
        Handles the CancelRegistration action requests.
        Deactivates the Completion Profile specified by the passed in registration_key value.

        Args:
            registration_data (dict): The fetched registration data.

        Returns:
            - response message
            - response status code - 200 for successful deactivation, 404 if can't find
                                     the completion profile based on the registration_key
        """
        registration_key = registration_data[c.REG_REGISTRATION_KEY]
        reference_id = registration_data[c.REG_REFERENCE_ID]

        try:
            completion_profile = CompletionProfile.objects.get(registration_key=registration_key)
            completion_profile.deactivate()

            msg = 'Completion profile with registration key [{}] deactivated.'.format(registration_key)
            LOG.info(msg)

            self.update_registration_status_request(
                reg_key=registration_key,
                ref_id=reference_id,
                status=c.REG_CANCELLATION_PROCESSED_STATUS
            )
            return msg, 200
        except CompletionProfile.DoesNotExist:
            msg = 'Completion Profile with registration key {reg_key} does not exist'.format(
                reg_key=registration_key
            )
            LOG.error(msg)
            self.update_registration_status_request(
                reg_key=registration_key,
                ref_id=reference_id,
                status=c.REG_CANCELLATION_REJECTED_STATUS
            )
            return msg, 404
        except Exception as e:  # pylint: disable=broad-except
            msg = self.handle_broad_exception(c.UPDATE_REGISTRATION_ACTION, registration_key, reference_id, e)
            return msg, 400

    def post(self, request):
        """
        POST request handler. Handles the action requests from Ed2go. Actions supported:
            * NewRegistration - creates a new user and/or a new course registration
            * UpdateRegistration - updates a user's information
            * CancelRegistration - deactivates the corresponding CompletionProfile object

        Returns:
            Response with code 200 if the request was completed.
            Response with code 400 if the request was not valid or the action is not supported.
        """
        valid, msg = request_valid(request.data, c.ACTION_REQUEST)
        if not valid:
            return Response(msg, status=400)

        action = request.data.get(c.ACTION)
        if action != c.GET_REGISTRATION_ACTION:
            msg = 'Action {action} not supported.'.format(action=action)
            request_info = get_request_info(request)
            LOG.error(msg)
            LOG.info(request_info)
            return Response(msg, status=400)

        registration_key = request.data.get(c.REGISTRATION_KEY)
        registration_data = get_registration_data(registration_key)
        registration_action = registration_data[c.REG_ACTION]

        if registration_action == c.NEW_REGISTRATION_ACTION:
            msg, status_code = self.new_registration_action_handler(registration_data)
        elif registration_action == c.UPDATE_REGISTRATION_ACTION:
            msg, status_code = self.update_registration_action_handler(registration_data)
        elif registration_action == c.CANCEL_REGISTRATION_ACTION:
            msg, status_code = self.cancel_registration_action_handler(registration_data)
        else:
            msg = 'Registration action {action} not supported.'.format(action=registration_action)
            request_info = get_request_info(request)
            status_code = 400
            LOG.error(msg)
            LOG.info(request_info)

        return Response(msg, status=status_code)


class CourseSessionView(APIView):
    def post(self, request):
        """
        POST requests handler.
        These requests are treated as user activity updates.

        Args:
            request (WSGIRequest): request that should contain information about the user
                and the course where the user activity is happening.
        Returns:
            Returns a 204 status code response.
        """
        course_id = request.POST['course_id']
        username = request.POST['user']
        user = User.objects.get(username=username)
        course_key = CourseKey.from_string(course_id)

        session, _ = CourseSession.objects.get_or_create(user=user, course_key=course_key, active=True)
        session.update()
        return Response(status=204)


class ContentViewedView(APIView):
    def post(self, request):
        """
        POST requests handler.
        Sets a subsection as viewed.
        usage_id = request.POST['usage_id']

        Args:
            request (WSGIRequest): request that should contain information
            about the subsection usage ID.
        Returns:
            Returns a 204 status code response.
        """
        usage_id = request.POST['usage_id']
        usage_key = UsageKey.from_string(usage_id)
        marked = ChapterProgress.mark_subsection_viewed(
            request.user,
            usage_key.course_key,
            usage_key.block_id
        )
        return Response(status=204 if marked else 404)
