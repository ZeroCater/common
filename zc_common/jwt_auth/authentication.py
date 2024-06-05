import jwt
from django.utils.encoding import smart_str
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.utils import jwt_decode_handler


class User(object):
    """
    A class that emulates Django's auth User, for use with microservices where
    the actual User is unavailable. Surfaces via `request.user`.
    """

    def __init__(self, **kwargs):
        self.pk = kwargs.pop('pk', None) or kwargs.pop('id', None)
        self.id = self.pk
        self.roles = []
        self.company_permissions = {}

        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

    def is_authenticated(self):
        # Roles (i.e. anonymous, user, etc) are handled by permissions classes
        return True

    def get_roles(self):
        """
        For testing purposes only. Emulates `get_roles` in
        https://github.com/ZeroCater/mp-users/blob/master/users/models.py
        """
        return self.roles


class JWTAuthentication(BaseAuthentication):
    """
    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string specified in the setting
    `JWT_AUTH_HEADER_PREFIX`. For example:

        Authorization: JWT eyJhbGciOiAiSFMyNTYiLCAidHlwIj
    """
    www_authenticate_realm = 'api'

    @staticmethod
    def get_jwt_value(request):
        auth = get_authorization_header(request).split()
        auth_header_prefix = api_settings.JWT_AUTH_HEADER_PREFIX.lower()

        if not auth or smart_str(auth[0].lower()) != auth_header_prefix:
            return None

        if len(auth) == 1:  # pragma: no cover
            msg = 'Invalid Authorization header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:  # pragma: no cover
            msg = 'Invalid Authorization header. Credentials string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        return auth[1]

    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        jwt_value = self.get_jwt_value(request)
        if jwt_value is None:
            raise exceptions.NotAuthenticated()

        try:
            payload = jwt_decode_handler(jwt_value)
        except jwt.ExpiredSignature:  # pragma: no cover
            msg = 'Signature has expired.'
            raise exceptions.AuthenticationFailed(msg)
        except jwt.DecodeError:  # pragma: no cover
            msg = 'Error decoding signature.'
            raise exceptions.AuthenticationFailed(msg)
        except jwt.InvalidTokenError:  # pragma: no cover
            raise exceptions.AuthenticationFailed()
        except Exception as ex:
            raise exceptions.AuthenticationFailed(ex.message)

        user = User(**payload)

        return user, jwt_value

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return '{0} realm="{1}"'.format(api_settings.JWT_AUTH_HEADER_PREFIX, self.www_authenticate_realm)
