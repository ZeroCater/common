import re
from distutils.util import strtobool

from django.db.models import BooleanField, FieldDoesNotExist
from django.db.models.fields.related import ManyToManyField
from django.utils import six

# DjangoFilterBackend was moved to django-filter and deprecated/moved from DRF in version 3.6
try:
    from rest_framework.filters import DjangoFilterBackend
except ImportError:
    from django_filters.rest_framework import DjangoFilterBackend


class JSONAPIFilterBackend(DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_class = self.get_filter_class(view, queryset)
        primary_key = queryset.model._meta.pk.name

        query_params = {}

        for param, value in six.iteritems(request.query_params):
            match = re.search(r'^filter\[(\w+)\]$', param)
            if match:
                filter_string = match.group(1)
                filter_string_parts = filter_string.split('__')

                if len(filter_string_parts) > 1:
                    field_name = '__'.join(filter_string_parts[:-1])
                else:
                    field_name = filter_string_parts[0]

                if field_name not in view.filter_fields.keys():
                    return queryset.none()

                if len(filter_string) > 1 and field_name == 'id':
                    filter_string_parts[0] = primary_key
                    query_params['__'.join(filter_string_parts)] = value

                try:
                    is_many_to_many_field = isinstance(getattr(queryset.model, filter_string).field, ManyToManyField)
                    if is_many_to_many_field:
                        value = value.split(',')
                except AttributeError:
                    pass

                # Allow 'true' or 'false' as values for boolean fields
                try:
                    if isinstance(queryset.model._meta.get_field(field_name), BooleanField):
                        value = bool(strtobool(value))
                except FieldDoesNotExist:
                    pass

                query_params[filter_string] = value

        if filter_class:
            return filter_class(query_params, queryset=queryset).qs

        return queryset
