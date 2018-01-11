from django.conf.urls import include, patterns, url

from ed2go.views import SSOView

urlpatterns = patterns(
    '',
    url(r'api/', include('ed2go.api.urls', namespace='api')),
    url(r'sso/$', SSOView.as_view(), name="sso"),
)
