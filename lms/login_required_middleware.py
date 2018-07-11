from django.conf import settings
from django.http import HttpResponseRedirect
from waffle import switch_is_active

from ed2go.constants import REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN


class LoginRequiredMiddleware:
    """
    Middleware that requires a user to be authenticated to view any page other
    than ED2GO_LOGIN_URL. Exemptions to this requirement can optionally be specified
    in settings via a list of regular expressions in LOGIN_EXEMPT_URLS (which
    you can copy from your urls.py).
    Requires authentication middleware and template context processors to be
    loaded. You'll get an error if they aren't.
    """
    def process_request(self, request):
        assert hasattr(request, 'user')
        # If REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN is active, every HTTP request on the LMS will be
        # redirected to ED2GO LOGIN URL
        if switch_is_active(REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN):
            if not request.user.is_authenticated():
                return HttpResponseRedirect(settings.STUDENT_LOGIN_URL)
