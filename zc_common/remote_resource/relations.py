from collections import OrderedDict
import json
import six

from django.db.models.manager import BaseManager
from rest_framework.relations import *
from rest_framework_json_api.relations import ResourceRelatedField

from zc_common.remote_resource.models import *


class RemoteResourceField(ResourceRelatedField):
    def __init__(self, related_resource_path=None, **kwargs):
        if 'model' not in kwargs:
            kwargs['model'] = RemoteResource
        if not kwargs.get('read_only', None):
            # The queryset is required to be not None, but not used
            #   due to the overriding of the methods below.
            kwargs['queryset'] = {}

        if related_resource_path is None:
            raise NameError('related_resource_path parameter must be provided')

        self.related_resource_path = related_resource_path

        super(RemoteResourceField, self).__init__(**kwargs)

    def get_links(self, obj=None, lookup_field='pk'):
        request = self.context.get('request', None)
        view = self.context.get('view', None)
        return_data = OrderedDict()

        kwargs = {lookup_field: getattr(obj, lookup_field) if obj else view.kwargs[lookup_field]}

        self_kwargs = kwargs.copy()
        self_kwargs.update({'related_field': self.field_name if self.field_name else self.parent.field_name})
        self_link = self.get_url('self', self.self_link_view_name, self_kwargs, request)

        # Construct the related link using the passed related_resource_path
        # self.source is the field name; getattr(obj, self.source) returns the
        # RemoteResource object or RelatedManager in the case of a to-many relationship.
        related_obj = getattr(obj, self.source)
        if isinstance(related_obj, BaseManager):
            list_of_ids = related_obj.values_list('pk', flat=True)
            query_parameters = unquote(urlencode({'ids[]': list_of_ids}, doseq=True))
            related_path = self.related_resource_path.format(pk=query_parameters)
        else:
            related_path = self.related_resource_path.format(pk=related_obj.pk)
        related_link = request.build_absolute_uri(related_path)

        if self_link:
            return_data.update({'self': self_link})
        if related_link:
            return_data.update({'related': related_link})
        return return_data

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
