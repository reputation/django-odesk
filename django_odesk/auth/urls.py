from django.conf.urls import patterns, url

urlpatterns = patterns(
    'django_odesk.auth.views',
    url(r'^authenticate/$', 'authenticate'),
    url(r'^callback/$', 'callback'),
)
