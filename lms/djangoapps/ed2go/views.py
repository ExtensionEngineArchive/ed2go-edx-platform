import logging

from django.conf import settings
from django.contrib.auth import login
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from opaque_keys.edx.keys import CourseKey

from courseware.courses import get_course_by_id
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.features.course_experience.utils import get_course_outline_block_tree

from ed2go import constants
from ed2go.registration import get_or_create_user_completion_profile
from ed2go.utils import request_valid

LOG = logging.getLogger(__name__)


class LearningPathView(View):
    """Learning path page view."""
    @method_decorator(login_required)
    @method_decorator(cache_control(no_cache=True, no_store=True, must_revalidate=True))
    def get(self, request, course_id, **kwargs):
        """
        Displays the learning path page for the specified course.
        """
        course_key = CourseKey.from_string(course_id)
        course = get_course_by_id(course_key, depth=2)
        course_block_tree = get_course_outline_block_tree(request, course_id)

        context = {
            'course': course,
            'course_tree': course_block_tree,
            'LANGUAGE_CODE': request.LANGUAGE_CODE,
            'learning_path_class': 'active',
            'platform_name': configuration_helpers.get_value('PLATFORM_NAME', settings.PLATFORM_NAME),
            'request': request,
        }
        return render_to_response('ed2go/learning_path.html', context)


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
        users, or create a new CompletionProfile object, or a new user altogether.

        At the end of this request there needs to be:
            * a user object corresponding with the registration data gathered
              from Ed2go registration service endpoint
            * a new or updated CompletionProfile object
            * the user needs to be logged in
            * the user needs to be redirected to the course in corresponding
              CompletionProfile object.

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
        user, completion_profile = get_or_create_user_completion_profile(registration_key)

        user.backend = settings.AUTHENTICATION_BACKENDS[0]
        login(request, user)
        return HttpResponseRedirect(
            reverse('course_root', kwargs={'course_id': completion_profile.course_key})
        )
