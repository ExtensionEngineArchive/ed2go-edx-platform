from django.conf.urls import include, patterns, url


urlpatterns = patterns(
    '',
    url(r'api/', include('ed2go.api.urls', namespace='api')),
)
