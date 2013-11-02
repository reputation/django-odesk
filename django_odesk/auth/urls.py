from django.conf.urls.defaults import patterns, url

urlpatterns = patterns(
    'django_odesk.auth.views',
    url(r'^authenticate/$', 'authenticate'),
    url(r'^callback/$', 'callback'),
)
