from django.db.models import CharField, TextField
from django.db.models import Model
from django.db.models.manager import Manager
from django.db.models.query import QuerySet
from rest_framework import viewsets
from rest_framework.exceptions import MethodNotAllowed
from rest_framework_json_api.views import RelationshipView as OldRelView

from zc_common.remote_resource.models import RemoteResource
from zc_common.remote_resource.serializers import ResourceIdentifierObjectSerializer


class ModelViewSet(viewsets.ModelViewSet):
    """
    This class overwrites the ModelViewSet's list method, which handles
    requests made to the collection's base endpoint (/collection), in
    order to provide support for filtering via the filter[] query parameter.

    Inheriting from this class, along with adding the filter backend, will properly
    handle requests made to /collection as well as /collection?filter[name]=test.
    It's also possible to filter by a collection of primary keys, for example:
    /collection?filter[id__in]=1,2,3
    Requests to filter on keys that do not exist will return an empty set.
    """

    @property
    def filterset_fields(self):
        queryset = self.get_queryset()
        return_fields = {}

        fields = queryset.model._meta.get_fields()
        for field in fields:
            # For backwards compatibility GenericForeignKey should not be
            # included in the results.
            if field.is_relation and field.many_to_one and field.related_model is None:
                continue
            # Relations to child proxy models should not be included.
            if (field.model != queryset.model._meta.model and
                    field.model._meta.concrete_model == queryset.model._meta.concrete_model):
                continue

            name = field.attname if hasattr(field, 'attname') else field.name
            if hasattr(field, 'primary_key') and field.primary_key:
                return_fields['id'] = ['in', 'exact']
            elif CharField in field.__class__.__mro__ or TextField in field.__class__.__mro__:
                return_fields[name] = ['icontains', 'exact']
            else:
                return_fields[name] = ['exact']

        return return_fields

    def has_ids_query_params(self):
        return hasattr(self.request, 'query_params') and 'filter[id__in]' in self.request.query_params


class RelationshipView(OldRelView):
    serializer_class = ResourceIdentifierObjectSerializer

    def patch(self, request, *args, **kwargs):
        """
        Restricting PATCH requests made to the relationship view temporarily to
        prevent the possibility of data corruption when PATCH requests are made
        to to-many related resources. This override will not be necessary
        once a fix is made upstream.

        See:
        https://github.com/django-json-api/django-rest-framework-json-api/issues/242
        """
        raise MethodNotAllowed('PATCH')

    def _instantiate_serializer(self, instance):
        if isinstance(instance, RemoteResource):
            return ResourceIdentifierObjectSerializer(instance=instance)

        if isinstance(instance, Model) or instance is None:
            return self.get_serializer(instance=instance)
        else:
            if isinstance(instance, (QuerySet, Manager)):
                instance = instance.all()

            return self.get_serializer(instance=instance, many=True)
