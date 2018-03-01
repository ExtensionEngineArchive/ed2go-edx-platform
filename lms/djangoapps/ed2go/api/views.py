import requests
from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from rest_framework.response import Response
from rest_framework.views import APIView

from ed2go import constants
from ed2go.models import CompletionProfile, CourseSession
from ed2go.registration import get_or_create_user_completion_profile, update_registration
from ed2go.utils import request_valid


class ActionView(APIView):
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
        valid, msg = request_valid(request.data, constants.ACTION_REQUEST)
        if not valid:
            return Response(msg, status=400)

        action = request.data.get(constants.ACTION)
        registration_key = request.data.get(constants.REGISTRATION_KEY)

        if action == 'NewRegistration':
            user, completion_profile = get_or_create_user_completion_profile(registration_key)
            msg = 'User {user} created and enrolled into {course}.'.format(
                user=user.username,
                course=completion_profile.course_key
            )
        elif action == 'UpdateRegistration':
            update_registration(registration_key)
            msg = 'User {user} information updated.'.format(user=user.username)
        elif action == 'CancelRegistration':
            CompletionProfile.objects.get(registration_key=registration_key).deactivate()
            msg = 'Completion profile deactivated.'
        else:
            return Response('Action %s not supported.' % action, status=400)
        return Response(msg, status=200)


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
