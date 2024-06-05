"""
Renderers
"""
import copy
from collections import OrderedDict
import os
import ujson

import inflection
from django.db.models import Manager
import six
from rest_framework import relations
from rest_framework.serializers import BaseSerializer, Serializer, ListSerializer
from rest_framework.settings import api_settings

from rest_framework_json_api import utils
from rest_framework_json_api import renderers

from zc_common.remote_resource.relations import RemoteResourceField
from zc_common.remote_resource import utils as zc_common_utils
from zc_events.exceptions import RequestTimeout


core_module_name = os.environ.get('DJANGO_SETTINGS_MODULE').split('.')[0]
core_module = __import__(core_module_name)
event_client = core_module.event_client


# `format_keys()` was replaced with `format_field_names()` from rest_framework_json_api in 3.0.0
def key_formatter():
    try:
        return zc_common_utils.format_keys
    except AttributeError:
        return utils.format_keys


class RemoteResourceIncludeError(Exception):

    def __init__(self, field, data=None):
        self.field = field
        self.message = "There was an error including the field {}".format(field)

        data['meta'] = {'include_field': field}
        self.data = [data]

    def __str__(self):
        return self.message


class RemoteResourceIncludeTimeoutError(RemoteResourceIncludeError):

    def __init__(self, field):
        self.field = field
        self.message = "Timeout error requesting remote resource {}".format(field)

        self.data = [{
            "status": "503",
            "source": {
                "pointer": "/data"
            },
            "meta": {
                "include_field": field,
            },
            "detail": self.message
        }]


class JSONRenderer(renderers.JSONRenderer):
    """
    This is s modification of renderers in (v 2.2)
    https://github.com/django-json-api/django-rest-framework-json-api
    """
    @classmethod
    def extract_attributes(cls, fields, resource):
        """
        @amberylx 2020-01-10: Copied from djangorestframework-jsonapi v3.0.0 in order to override the call to
        `utils.format_field_names(data)` to our own function of `format_keys()`, which is a copy of the library's
        old (pre-v3.0) function.
        """
        data = OrderedDict()
        for field_name, field in iter(fields.items()):
            # ID is always provided in the root of JSON API so remove it from attributes
            if field_name == 'id':
                continue
            # don't output a key for write only fields
            if fields[field_name].write_only:
                continue
            # Skip fields with relations
            if isinstance(
                    field, (relations.RelatedField, relations.ManyRelatedField, BaseSerializer)
            ):
                continue

            # Skip read_only attribute fields when `resource` is an empty
            # serializer. Prevents the "Raw Data" form of the browsable API
            # from rendering `"foo": null` for read only fields
            try:
                resource[field_name]
            except KeyError:
                if fields[field_name].read_only:
                    continue

            data.update({
                field_name: resource.get(field_name)
            })

        return key_formatter()(data)

    @classmethod
    def extract_included(cls, request, fields, resource, resource_instance, included_resources):
        # this function may be called with an empty record (example: Browsable Interface)
        if not resource_instance:
            return

        included_data = list()
        current_serializer = fields.serializer
        context = current_serializer.context
        included_serializers = getattr(current_serializer, "included_serializers", [])
        included_resources = copy.copy(included_resources)
        included_resources = [inflection.underscore(value) for value in included_resources]

        for field_name, field in six.iteritems(fields):
            # Skip URL field
            if field_name == api_settings.URL_FIELD_NAME:
                continue

            # Skip fields without relations or serialized data
            if not isinstance(field, (relations.RelatedField, relations.ManyRelatedField, BaseSerializer)):
                continue

            try:
                included_resources.remove(field_name)
            except ValueError:
                # Skip fields not in requested included resources
                # If no child field, directly continue with the next field
                if field_name not in [node.split('.')[0] for node in included_resources]:
                    continue

            try:
                relation_instance = getattr(resource_instance, field_name)
            except AttributeError:
                try:
                    # For ManyRelatedFields if `related_name` is not set we need to access `foo_set` from `source`
                    relation_instance = getattr(resource_instance, field.child_relation.source)
                except AttributeError:
                    if not hasattr(current_serializer, field.source):
                        continue
                    serializer_method = getattr(current_serializer, field.source)
                    relation_instance = serializer_method(resource_instance)

            if isinstance(relation_instance, Manager):
                relation_instance = relation_instance.all()

            new_included_resources = [key.replace('%s.' % field_name, '', 1)
                                      for key in included_resources
                                      if field_name == key.split('.')[0]]
            serializer_data = resource.get(field_name)

            if isinstance(field, RemoteResourceField):
                user_id = getattr(request.user, 'id', None)
                roles = request.user.roles
                pk = serializer_data.get('id')

                include = ",".join(new_included_resources)
                try:
                    remote_resource = event_client.get_remote_resource_data(
                        field_name, pk=pk, user_id=user_id,
                        include=include, page_size=1000, roles=roles)

                    body = ujson.loads(remote_resource['body'])

                    if 400 <= remote_resource['status'] < 600:
                        raise RemoteResourceIncludeError(field_name, body["errors"][0])
                except RequestTimeout:
                    raise RemoteResourceIncludeTimeoutError(field_name)

                included_data.append(body['data'])

                if body.get('included'):
                    included_data.extend(body['included'])

                # We continue here since RemoteResourceField inherits
                # form ResourceRelatedField which is a RelatedField
                continue

            if isinstance(field, relations.ManyRelatedField):
                serializer_class = included_serializers[field_name]
                field = serializer_class(relation_instance, many=True, context=context)
                serializer_data = field.data

            if isinstance(field, relations.RelatedField):
                if relation_instance is None:
                    continue

                many = field._kwargs.get('child_relation', None) is not None
                serializer_class = included_serializers[field_name]
                field = serializer_class(relation_instance, many=many, context=context)
                serializer_data = field.data

            if isinstance(field, ListSerializer):
                serializer = field.child
                relation_type = utils.get_resource_type_from_serializer(serializer)
                relation_queryset = list(relation_instance)

                # Get the serializer fields
                serializer_fields = utils.get_serializer_fields(serializer)
                if serializer_data:
                    for position in range(len(serializer_data)):
                        serializer_resource = serializer_data[position]
                        nested_resource_instance = relation_queryset[position]
                        resource_type = (
                            relation_type or
                            utils.get_resource_type_from_instance(nested_resource_instance)
                        )
                        included_data.append(
                            cls.build_json_resource_obj(
                                serializer_fields,
                                serializer_resource,
                                nested_resource_instance,
                                resource_type,
                                serializer,
                            )
                        )
                        included_data.extend(
                            cls.extract_included(
                                request, serializer_fields, serializer_resource,
                                nested_resource_instance, new_included_resources
                            )
                        )

            if isinstance(field, Serializer):

                relation_type = utils.get_resource_type_from_serializer(field)

                # Get the serializer fields
                serializer_fields = utils.get_serializer_fields(field)
                if serializer_data:
                    included_data.append(
                        cls.build_json_resource_obj(
                            serializer_fields, serializer_data,
                            relation_instance, relation_type, field)
                    )
                    included_data.extend(
                        cls.extract_included(
                            request, serializer_fields, serializer_data,
                            relation_instance, new_included_resources
                        )
                    )

        return key_formatter()(included_data)

    def render(self, data, accepted_media_type=None, renderer_context=None):

        view = renderer_context.get("view", None)
        request = renderer_context.get("request", None)

        # Get the resource name.
        resource_name = utils.get_resource_name(renderer_context)

        # If this is an error response, skip the rest.
        if resource_name == 'errors':
            return self.render_errors(data, accepted_media_type, renderer_context)

        # if response.status_code is 204 then the data to be rendered must
        # be None
        response = renderer_context.get('response', None)
        if response is not None and response.status_code == 204:
            return super(renderers.JSONRenderer, self).render(
                None, accepted_media_type, renderer_context
            )

        from rest_framework_json_api.views import RelationshipView
        if isinstance(view, RelationshipView):
            return self.render_relationship_view(data, accepted_media_type, renderer_context)

        # If `resource_name` is set to None then render default as the dev
        # wants to build the output format manually.
        if resource_name is None or resource_name is False:
            return super(renderers.JSONRenderer, self).render(
                data, accepted_media_type, renderer_context
            )

        json_api_data = data
        json_api_included = list()
        # initialize json_api_meta with pagination meta or an empty dict
        json_api_meta = data.get('meta', {}) if isinstance(data, dict) else {}

        if data and 'results' in data:
            serializer_data = data["results"]
        else:
            serializer_data = data

        serializer = getattr(serializer_data, 'serializer', None)

        included_resources = utils.get_included_resources(request, serializer)

        if serializer is not None:

            # Get the serializer fields
            fields = utils.get_serializer_fields(serializer)

            # Extract root meta for any type of serializer
            json_api_meta.update(self.extract_root_meta(serializer, serializer_data))

            try:
                if getattr(serializer, 'many', False):
                    json_api_data = list()

                    for position in range(len(serializer_data)):
                        resource = serializer_data[position]  # Get current resource
                        resource_instance = serializer.instance[position]  # Get current instance

                        json_resource_obj = self.build_json_resource_obj(
                            fields, resource, resource_instance, resource_name, serializer,
                        )
                        meta = self.extract_meta(serializer, resource)
                        if meta:
                            json_resource_obj.update({'meta': key_formatter()(meta)})
                        json_api_data.append(json_resource_obj)

                        included = self.extract_included(request, fields, resource,
                                                         resource_instance, included_resources)
                        if included:
                            json_api_included.extend(included)
                else:
                    resource_instance = serializer.instance
                    json_api_data = self.build_json_resource_obj(
                        fields, serializer_data, resource_instance, resource_name, serializer,
                    )

                    meta = self.extract_meta(serializer, serializer_data)
                    if meta:
                        json_api_data.update({'meta': key_formatter()(meta)})

                    included = self.extract_included(request, fields, serializer_data,
                                                     resource_instance, included_resources)
                    if included:
                        json_api_included.extend(included)
            except RemoteResourceIncludeError as e:
                return self.render_errors(e.data, accepted_media_type)

        # Make sure we render data in a specific order
        render_data = OrderedDict()

        if isinstance(data, dict) and data.get('links'):
            render_data['links'] = data.get('links')

        # format the api root link list
        if view.__class__ and view.__class__.__name__ == 'APIRoot':
            render_data['data'] = None
            render_data['links'] = json_api_data
        else:
            render_data['data'] = json_api_data

        if len(json_api_included) > 0:
            # Iterate through compound documents to remove duplicates
            seen = set()
            unique_compound_documents = list()
            for included_dict in json_api_included:
                type_tuple = tuple((included_dict['type'], included_dict['id']))
                if type_tuple not in seen:
                    seen.add(type_tuple)
                    unique_compound_documents.append(included_dict)

            # Sort the items by type then by id
            render_data['included'] = sorted(unique_compound_documents, key=lambda item: (item['type'], item['id']))

        if json_api_meta:
            render_data['meta'] = key_formatter()(json_api_meta)

        return super(renderers.JSONRenderer, self).render(
            render_data, accepted_media_type, renderer_context
        )
