from collections import OrderedDict

from django.db.models import OneToOneField
from django.db.models.fields import related
from rest_framework.relations import ManyRelatedField
from rest_framework.serializers import DecimalField
from rest_framework.settings import api_settings
from rest_framework.utils.field_mapping import ClassLookupDict
from rest_framework_json_api.metadata import JSONAPIMetadata
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_related_resource_type

from zc_common.remote_resource.relations import RemoteResourceField
from zc_common.remote_resource.models import RemoteForeignKey


class RelationshipMetadata(JSONAPIMetadata):
    relation_type_lookup = ClassLookupDict({
        related.ManyToManyDescriptor: 'ManyToMany',
        related.ReverseManyToOneDescriptor: 'OneToMany',
        related.ForwardManyToOneDescriptor: 'ManyToOne',
        related.ReverseOneToOneDescriptor: 'OneToOne',
        OneToOneField: 'OneToOne',
        RemoteForeignKey: 'ManyToOne',
    })

    def get_serializer_info(self, serializer):
        """
        @amberylx 2020-01-10: Copied from djangorestframework-jsonapi v2.2.0 in order to remove the call to
        `format_value` on the keys of the metadata object.
        """
        if hasattr(serializer, 'child'):
            # If this is a `ListSerializer` then we want to examine the
            # underlying child serializer instance instead.
            serializer = serializer.child

        # Remove the URL field if present
        serializer.fields.pop(api_settings.URL_FIELD_NAME, None)

        return OrderedDict([
            (field_name, self.get_field_info(field))
            for field_name, field in serializer.fields.items()
        ])

    def get_field_info(self, field):
        field_info = super(RelationshipMetadata, self).get_field_info(field)
        if isinstance(field, (RemoteResourceField, ManyRelatedField, ResourceRelatedField)):
            model_class = field.parent.Meta.model
            model_field = getattr(model_class, field.source)

            if hasattr(model_field, 'field') and isinstance(model_field.field, OneToOneField):
                # ForwardManyToOneDescriptor is used for OneToOneField also, so we have to override
                model_field = model_field.field

            field_info['relationship_type'] = self.relation_type_lookup[model_field]
            field_info['relationship_resource'] = get_related_resource_type(field)

            if field_info['relationship_resource'] == 'RemoteResource':
                field_info['relationship_resource'] = model_field.type

        if isinstance(field, DecimalField):
            field_info['decimal_places'] = getattr(field, 'decimal_places', 2)
        return field_info
