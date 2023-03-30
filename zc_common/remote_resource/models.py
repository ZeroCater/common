from __future__ import unicode_literals

from django.db import models
from django.db.models import signals


class RemoteResource(object):

    def __init__(self, type_name, pk):

        self.type = str(type_name) if type_name else None
        self.id = str(pk) if pk else None


class RemoteForeignKey(models.CharField):
    is_relation = True
    many_to_many = False
    many_to_one = True
    one_to_many = False
    one_to_one = False
    related_model = None
    remote_field = None

    description = "A foreign key pointing to an external resource"

    def __init__(self, type_name, *args, **kwargs):
        if 'max_length' not in kwargs:
            kwargs['max_length'] = 50

        if 'db_index' not in kwargs:
            kwargs['db_index'] = True

        if 'db_column' not in kwargs:
            kwargs['db_column'] = "%s_id" % type_name.lower()

        self.type = type_name

        super(RemoteForeignKey, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection, context):
        return RemoteResource(self.type, value)

    def to_python(self, value):
        if isinstance(value, RemoteResource):
            return value.id

        if isinstance(value, basestring):
            return value

        if value is None:
            return value

        raise ValueError("Can not convert value to a RemoteResource properly")

    def deconstruct(self):
        name, path, args, kwargs = super(RemoteForeignKey, self).deconstruct()

        args = tuple([self.type] + list(args))

        del kwargs['max_length']

        return name, path, args, kwargs

    def contribute_to_class(self, cls, name, **kwargs):
        self.set_attributes_from_name(name)
        self.name = name
        self.model = cls
        cls._meta.add_field(self)

        setattr(cls, name, self)
