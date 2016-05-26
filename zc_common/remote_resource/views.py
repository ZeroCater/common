from django.db import IntegrityError
from django.db.models import Model
from django.db.models.query import QuerySet
from django.db.models.manager import Manager
from django.http import Http404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework_json_api.views import RelationshipView

from zc_common.remote_resource.models import RemoteResource
from zc_common.remote_resource.serializers import ResourceIdentifierObjectSerializer


class ModelViewSet(viewsets.ModelViewSet):
    """
    This class overwrites the ModelViewSet's retrieve method, which normally provides
    a serialized representation of a single object with the ID provided in the url
    parameter such as `/collection/1`. This allows the retrieve route to serialize any
    arbitrary list of ids provided to it, comma-separated, such as `/collection/1,2,3`.
    """
    def retrieve(self, request, *args, **kwargs):
        pks = kwargs.pop('pk', None)
        if pks:
            pks = pks.split(',')
            try:
                queryset = self.filter_queryset(self.get_queryset().filter(pk__in=pks))
            except (ValueError, IntegrityError):
                raise Http404

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return super(ModelViewSet, self).retrieve(request, *args, **kwargs)


class RelationshipView(RelationshipView):
    serializer_class = ResourceIdentifierObjectSerializer

    def _instantiate_serializer(self, instance):
        if isinstance(instance, RemoteResource):
            return ResourceIdentifierObjectSerializer(instance=instance)

        if isinstance(instance, Model) or instance is None:
            return self.get_serializer(instance=instance)
        else:
            if isinstance(instance, (QuerySet, Manager)):
                instance = instance.all()

            return self.get_serializer(instance=instance, many=True)
