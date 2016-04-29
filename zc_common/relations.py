from collections import OrderedDict
import json
import six

from rest_framework.relations import *
from rest_framework_json_api.relations import ResourceRelatedField

from remote_resource.models import *


class RemoteResourceField(ResourceRelatedField):
    def __init__(self, *args, **kwargs):
        if 'model' not in kwargs:
            kwargs['model'] = RemoteResource
        if not kwargs.get('read_only', None):
            # The queryset is required to be not None, but not used
            #   due to the overriding of the methods below.
            kwargs['queryset'] = True
        super(RemoteResourceField, self).__init__(*args, **kwargs)

    def to_internal_value(self, data):
        if isinstance(data, six.text_type):
            try:
                data = json.loads(data)
            except ValueError:
                self.fail('incorrect_type', data_type=type(data).__name__)
        if not isinstance(data, dict):
            self.fail('incorrect_type', data_type=type(data).__name__)

        if 'type' not in data:
            self.fail('missing_type')

        if 'id' not in data:
            self.fail('missing_id')

        return RemoteResource(data['type'], data['id'])

    def to_representation(self, value):
        return OrderedDict([('type', value.type), ('id', str(value.id))])
