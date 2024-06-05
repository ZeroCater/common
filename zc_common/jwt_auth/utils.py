import jwt
from django.utils import encoding
from rest_framework_jwt.settings import api_settings
from .permissions import SERVICE_ROLES


def jwt_payload_handler(user):
    """Constructs a payload for a user JWT.
    This is a slimmed down version of the handler in
    https://github.com/GetBlimp/django-rest-framework-jwt/

    :param user: an object with `pk` and `get_roles()`
    :return: A dictionary that can be passed into `jwt_encode_handler`
    """

    payload = {
        'id': encoding.force_str(user.pk),
        'roles': user.get_roles(),
    }

    return payload


def service_jwt_payload_handler(service_name):
    """Constructs a payload for a service JWT.

    :param service_name: a string corresponding to the name of the service where this JWT will be sent
    :return: a dictionary that can be passed into `jwt_encode_handler`
    """
    payload = {
        'serviceName': service_name,
        'roles': SERVICE_ROLES
    }

    return payload


def jwt_encode_handler(payload):
    """Encodes a payload into a valid JWT.

    :param payload: a dictionary
    :return: an encoded JWT string
    """

    return jwt.encode(
        payload,
        api_settings.JWT_SECRET_KEY,
        api_settings.JWT_ALGORITHM
    ).decode('utf-8')
