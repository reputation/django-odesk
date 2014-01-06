import logging
import datetime

from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth import get_backends
from django.contrib.auth import login, REDIRECT_FIELD_NAME
from django.contrib.auth.models import User

from django_odesk.core.clients import DefaultClient
from django_odesk.auth import (
    ODESK_REDIRECT_SESSION_KEY, ODESK_TOKEN_SESSION_KEY, ENCRYPTION_KEY_NAME
)
from django_odesk.conf import settings
from encrypt import encrypt_token


def authenticate(request):
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
    request.session[ODESK_REDIRECT_SESSION_KEY] = redirect_to
    odesk_client = DefaultClient()
    authorize_url = odesk_client.auth.get_authorize_url()
    request.session['odesk_request_token'] = odesk_client.auth.request_token
    request.session['odesk_request_token_secret'] = \
        odesk_client.auth.request_token_secret

    return HttpResponseRedirect(authorize_url)


def callback(request, redirect_url=None):
    oauth_verifier = request.GET.get('oauth_verifier', None)
    request_token = request.session.pop('odesk_request_token', None)
    request_token_secret = request.session.pop('odesk_request_token_secret',
                                               None)
    odesk_client = DefaultClient(
        request_token=request_token,
        request_token_secret=request_token_secret
    )
    if oauth_verifier:
        try:
            oauth_access_token, oauth_access_token_secret = \
                odesk_client.auth.get_access_token(oauth_verifier)
            client = DefaultClient(
                oauth_access_token=oauth_access_token,
                oauth_access_token_secret=oauth_access_token_secret
            )
            user_info = client.auth.get_info()
            user_uid = user_info['auth_user']['uid']
        except Exception as exc:
            msg = "get_access_token({0}) failed with {1}, {2}".format(
                oauth_verifier, exc, request)
            logging.error(msg, exc_info=True)
            return HttpResponseRedirect(redirect_url or '/')

        if not settings.ODESK_AUTH_ONLY:
            if settings.ODESK_ENCRYPT_API_TOKEN:
                encryption_key, encrypted_token = encrypt_token(
                    oauth_access_token)
                put_in_session = encrypted_token
            else:
                put_in_session = oauth_access_token
            request.session[ODESK_TOKEN_SESSION_KEY] = put_in_session

        user = django_authenticate(token=oauth_access_token)
        if not user is None:
            login(request, user)
        else:
            email = user_info.get('auth_user', {}).get('mail')
            fname = user_info.get('auth_user', {}).get('first_name')
            lname = user_info.get('auth_user', {}).get('last_name')
            if email:
                user, created = User.objects.get_or_create(username=email,
                                                           email=email,
                                                           first_name=fname,
                                                           last_name=lname)
                if user:
                    backend = get_backends()[0]
                    user.token = oauth_access_token
                    user.backend = "%s.%s" % (backend.__module__,
                                              backend.__class__.__name__)
                    user.save()
                    login(request, user)

        if user.username == getattr(settings, 'ODESK_API_USER', None):
            request.session['access_token'] = oauth_access_token
            request.session['access_secret'] = oauth_access_token_secret

        redirect_url = request.session.pop(ODESK_REDIRECT_SESSION_KEY,
                                           redirect_url)

        response = HttpResponseRedirect(redirect_url or '/')
        if not settings.ODESK_AUTH_ONLY and settings.ODESK_ENCRYPT_API_TOKEN:
            expires = datetime.timedelta(hours=2) + \
                datetime.datetime.utcnow()

            # string conversion for django 1.2 somehow doesn't work either,
            # so I use max_age
            response.set_cookie(ENCRYPTION_KEY_NAME, encryption_key,
                                expires=expires, max_age=60*60*2)
        return response

    else:
        return HttpResponseRedirect(odesk_client.auth.get_authorize_url())
