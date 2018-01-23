from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import CourseSession


class CourseSessionView(APIView):
    def post(self, request):
        """
        POST requests handler.
        These requests are treated as user activity updates.

        Args:
            request (WSGIRequest): request that should contain information about the user
                and the course where the user activity is happening.
        Returns:
            Returns a 200 status code response.
        """
        course_id = request.POST['course_id']
        username = request.POST['user']
        user = User.objects.get(username=username)
        course_key = CourseKey.from_string(course_id)

        session, _ = CourseSession.objects.get_or_create(user=user, course_key=course_key, active=True)
        session.update()
        return Response(status=200)
