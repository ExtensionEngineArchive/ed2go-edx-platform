from django.conf import settings
from django.http import HttpResponseRedirect


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
        # If REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN is true, every HTTP request on the LMS will be
        # redirected to ED2GO LOGIN URL
        if settings.REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN:
            if not request.user.is_authenticated():
                return HttpResponseRedirect('https://www.ed2go.com/student-login/')
