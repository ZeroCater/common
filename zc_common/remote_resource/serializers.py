from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_json_api.utils import (
    get_resource_type_from_model, get_resource_type_from_instance)

from zc_common.remote_resource.models import RemoteResource


class ResourceIdentifierObjectSerializer(serializers.BaseSerializer):
    default_error_messages = {
        'incorrect_model_type': _('Incorrect model type. Expected {model_type}, received {received_type}.'),
        'does_not_exist': _('Invalid pk "{pk_value}" - object does not exist.'),
        'incorrect_type': _('Incorrect type. Expected pk value, received {data_type}.'),
    }

    model_class = None

    def __init__(self, *args, **kwargs):
        self.model_class = kwargs.pop('model_class', self.model_class)
        if 'instance' not in kwargs and not self.model_class:
            raise RuntimeError('ResourceIdentifierObjectsSerializer must be initialized with a model class.')
        super(ResourceIdentifierObjectSerializer, self).__init__(*args, **kwargs)

    def to_representation(self, instance):
        if isinstance(instance, RemoteResource):
            return {'type': instance.type, 'id': instance.id}

        return {
            'type': get_resource_type_from_instance(instance),
            'id': str(instance.pk)
        }

    def to_internal_value(self, data):
        model_class = get_resource_type_from_model(self.model_class)

        if model_class == "RemoteResource":
            return RemoteResource(data['type'], data['id'])

        if data['type'] != model_class:
            self.fail('incorrect_model_type', model_type=self.model_class, received_type=data['type'])
        pk = data['id']
        try:
            return self.model_class.objects.get(pk=pk)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', pk_value=pk)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data['pk']).__name__)


class IncludedDict(dict):

    def get(self, *args):
        return lambda *a: True


class RemoteResourceSerializer(object):
    included_serializers = IncludedDict()
