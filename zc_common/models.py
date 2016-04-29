from __future__ import unicode_literals
import exceptions

from django.db import models
from django_extensions.db.models import TimeStampedModel


class RemoteResource(object):
    def __init__(self, type_name, id):
        self.type = type_name
        self.id = id

class RemoteForeignKey(models.CharField):
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

        if isinstance(value, str):
            return value

        if value is None:
            return value

        raise ValueError("Can not convert value to a RemoteResource properly")

    def deconstruct(self):
        name, path, args, kwargs = super(RemoteForeignKey, self).deconstruct()

        args = tuple([self.type] + list(args))

        del kwargs["max_length"]

        return name, path, args, kwargs
