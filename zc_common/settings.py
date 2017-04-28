from django.conf import settings
from rest_framework.settings import APISettings

DEFAULTS = {
    'GATEWAY_ROOT_PATH': getattr(
        settings, 'GATEWAY_ROOT_PATH', os.environ.get('GATEWAY_ROOT_PATH', 'http://gateway:4000/'))
}

zc_settings = APISettings(None, DEFAULTS, None)
