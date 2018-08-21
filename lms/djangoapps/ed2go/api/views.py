from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey, UsageKey
from rest_framework.response import Response
from rest_framework.views import APIView

from ed2go import constants as c
from ed2go.exceptions import CompletionProfileAlreadyExists
from ed2go.models import CompletionProfile, CourseSession, ChapterProgress
from ed2go.registration import update_registration
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
        valid, msg = request_valid(request.data, c.ACTION_REQUEST)
        if not valid:
            return Response(msg, status=400)

        action = request.data.get(c.ACTION)
        registration_key = request.data.get(c.REGISTRATION_KEY)

        if action == c.NEW_REGISTRATION_ACTION:
            try:
                completion_profile = CompletionProfile.create(registration_key)
            except CompletionProfileAlreadyExists:
                msg = 'Completion Profile already exists for registration key {reg_key}'.format(
                    reg_key=registration_key
                )
                return Response(msg, status=400)

            msg = 'Completion Profile created for user {user} and course {course}.'.format(
                user=completion_profile.user.username,
                course=completion_profile.course_key
            )
            return Response(msg, status=201)
        elif action == c.UPDATE_REGISTRATION_ACTION:
            user = update_registration(registration_key)
            msg = 'User {user} information updated.'.format(user=user.username)
        elif action == c.CANCEL_REGISTRATION_ACTION:
            try:
                CompletionProfile.objects.get(registration_key=registration_key).deactivate()
            except CompletionProfile.DoesNotExist:
                return Response(
                    'Completion Profile with registration key {reg_key} does not exist'.format(
                        reg_key=registration_key
                    ),
                    status=404
                )
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
