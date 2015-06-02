import logging

from upwork import Client
from django.core.exceptions import ImproperlyConfigured
from django_odesk.conf import settings
from django_odesk.auth import ODESK_TOKEN_SESSION_KEY, ENCRYPTION_KEY_NAME
from django_odesk.auth.encrypt import decrypt_token


class DefaultClient(Client):

    def __init__(self, **attrs):
        public_key = settings.ODESK_PUBLIC_KEY
        secret_key = settings.ODESK_PRIVATE_KEY
        if not (public_key and secret_key):
            raise ImproperlyConfigured(
                "The django_odesk.core.clients.DefaultClient requires "+\
                "both ODESK_PUBLIC_KEY and ODESK_PRIVATE_KEY "+\
                "settings to be specified.")

        client_kwargs = {
            'oauth_access_token': attrs.pop('oauth_access_token', None),
            'oauth_access_token_secret': attrs.pop(
                'oauth_access_token_secret', None)
        }
        super(DefaultClient, self).__init__(
            public_key, secret_key, **client_kwargs
        )

        for key, value in attrs.items():
            setattr(self.auth, key, value)
