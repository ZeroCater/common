import re
from distutils.util import strtobool

from django.contrib.postgres.forms import SimpleArrayField
from django.contrib.postgres.fields import ArrayField
from django.db.models import BooleanField, FieldDoesNotExist, ForeignKey
from django.db.models.fields.related import ManyToManyField
from django import forms
import six

# DjangoFilterBackend was moved to django-filter and deprecated/moved from DRF in version 3.6
try:
    from rest_framework.filters import DjangoFilterBackend, Filter
    from rest_framework import filterset
except ImportError:
    from django_filters.rest_framework import DjangoFilterBackend, filterset
    from django_filters.rest_framework.filters import Filter
    from django_filters.filters import ModelChoiceFilter

# remote_model() was removed from django_filters in 2.0
try:
    try:
        from rest_framework.compat import get_related_model as remote_model
    except ImportError:
        from django_filters.compat import remote_model
except:
    pass


def remote_queryset(field):
    # remote_model() was removed from django_filters in 2.0
    try:
        model = remote_model(field)
    except:
        model = field.remote_field.model

    limit_choices_to = field.get_limit_choices_to()
    return model._base_manager.complex_filter(limit_choices_to)


class ArrayFilter(Filter):
    field_class = SimpleArrayField

    @property
    def field(self):
        # This property needs to be overriden because filters.Filter does not instantiate field_class with any
        # args by default, and SimpleArrayField requires an argument indicating the type of each element in the array
        self._field = self.field_class(forms.CharField(), required=False)
        return self._field


class JSONAPIFilterSet(filterset.FilterSet):
    class Meta:
        strict = True
        filter_overrides = {
            ArrayField: {
                'filter_class': ArrayFilter,
                'extra': lambda f: {
                    'lookup_expr': 'contains',
                }
            },
            # Overrides default definition in django_filters to allow us to use our own definition of
            # `remote_queryset`, which looks up allowable values via `_base_manager` rather than `_default_manager`
            ForeignKey: {
                'filter_class': ModelChoiceFilter,
                'extra': lambda f: {
                    'queryset': remote_queryset(f),
                }
            },
        }


class JSONAPIFilterBackend(DjangoFilterBackend):
    default_filter_set = JSONAPIFilterSet

    # This method takes the filter query string (looks something like ?filter[xxx]=yyy) and parses into parameters
    # that django_filters can interface with.
    #
    # Handles:
    #   ?filter[id]=1
    #   ?filter[id__in]=1,2,3
    #   ?filter[price__gte]=100
    #   ?filter[relatedobject__relatedobject]=1
    #   ?filter[relatedobject__relatedobject__in]=1,2,3
    #   ?filter[delivery_days__contains]=true  # filtering on ArrayField
    #   ?filter[active]=1  # filtering on Boolean values of 1, 0, true or false
    def _parse_filter_string(self, queryset, filter_class, filter_string, filter_value):
        filter_string_parts = filter_string.split('__')
        if len(filter_string_parts) > 1:
            field_name = '__'.join(filter_string_parts[:-1])
        else:
            field_name = filter_string_parts[0]

        # Translates the 'id' in ?filter[id]= into the primary key identifier, e.g. 'pk'
        if field_name == 'id':
            primary_key = queryset.model._meta.pk.name
            field_name = primary_key

        try:
            is_many_to_many_field = isinstance(getattr(queryset.model, filter_string).field, ManyToManyField)
            if is_many_to_many_field:
                filter_value = filter_value.split(',')
        except AttributeError:
            pass

        try:
            field_filter = filter_class.get_filters().get(field_name, None)
            is_array_filter = isinstance(field_filter, ArrayFilter)
            if is_array_filter:
                filter_value = filter_value.split(',')
        except AttributeError:
            pass

        # Allow 'true' or 'false' as values for boolean fields
        try:
            if isinstance(queryset.model._meta.get_field(field_name), BooleanField):
                filter_value = bool(strtobool(filter_value))
        except FieldDoesNotExist:
            pass

        filterset_data = {
            'field_name': field_name,
            'field_name_with_lookup': filter_string,
            'filter_value': filter_value
        }

        return filterset_data

    def filter_queryset(self, request, queryset, view):
        filter_class = self.get_filter_class(view, queryset)

        filters = []
        for param, value in six.iteritems(request.query_params):
            match = re.search(r'^filter\[(\w+)\]$', param)
            if match:
                filter_string = match.group(1)
                parsed_filter_string = self._parse_filter_string(queryset, filter_class, filter_string, value)
                filters.append(parsed_filter_string)

                for filter_ in filters:
                    if filter_['field_name'] not in view.filter_fields.keys():
                        return queryset.none()

        filterset_data = {filter_['field_name_with_lookup']: filter_['filter_value'] for filter_ in filters}
        if filter_class:
            return filter_class(filterset_data, queryset=queryset).qs

        return queryset
