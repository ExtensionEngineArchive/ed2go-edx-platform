import logging
from dateutil import parser

import requests
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http.response import HttpResponse, HttpResponseRedirect
from opaque_keys.edx.keys import CourseKey
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from ed2go import constants
from ed2go.models import CourseRegistration
from ed2go.registration import get_or_create_user_registration
from ed2go.utils import XMLHandler, generate_username, get_registration_data, request_valid
from student.models import CourseEnrollment, UserProfile

LOG = logging.getLogger(__name__)


class SSOView(View):
    """SSO request handler."""
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        """We want to exempt these calls from CSRF checks."""
        return super(SSOView, self).dispatch(*args, **kwargs)

    def post(self, request):
        """
        POST request handler. Handles the SSO requests from Ed2go.
        The request needs to be valid and have a registration key passed along.
        That registration key is then used to either retrieved already registered
        users, or create a new CourseRegistration object, or a new user altogether.

        At the end of this request there needs to be:
            * a user object corresponding with the registration data gathered
              from Ed2go registration service endpoint
            * a new or updated CourseRegistration object
            * the user needs to be logged in
            * the user needs to be redirected to the course in corresponding
              CourseRegistration object.

        Invalid requests will be redirect to the passed in ReturnURL parameter, if
        there is one, else a 400 error will be returned.
        """
        valid, msg = request_valid(request.POST, constants.SSO_REQUEST)
        if not valid:
            return_url = request.POST.get(constants.RETURN_URL)
            if return_url:
                LOG.info('Invalid SSO request. Redirecting to %s', return_url)
                return HttpResponseRedirect(return_url)
            return HttpResponse(msg, status=400)

        registration_key = request.POST[constants.REGISTRATION_KEY]
        user, course_registration = get_or_create_user_registration(registration_key)

        user.backend = settings.AUTHENTICATION_BACKENDS[0]
        login(request, user)
        return HttpResponseRedirect('/courses/{}'.format(course_registration.course_key))
