import json
import uuid

import boto
from boto.s3.key import Key

from django.conf import settings


def model_to_dict(instance, included_attributes=[]):
    """Returns a native python dict corresponding to selected attributes of a model instance."""

    def get_value(obj, field):
        field_value = getattr(obj, field)

        if callable(field_value):
            return field_value()
        return field_value

    data = {}

    for item in included_attributes:
        instance_attr_name = item[0] if isinstance(item, tuple) else item
        attr_name = item[1] if isinstance(item, tuple) else item

        attr_value = instance
        for attr in instance_attr_name.split('.'):
            attr_value = get_value(attr_value, attr)

            if not attr_value:
                break

        data.setdefault(attr_name, attr_value)

    return data


def event_payload(resource_type, resource_id, user_id, meta):
    return {
        'resource_type': resource_type,
        'resource_id': resource_id,
        'user_id': user_id,
        'meta': meta
    }


def save_to_s3file(data, aws_bucket_name, aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                   aws_secret_assess_key=settings.AWS_SECRET_ACCESS_KEY):
    connection = boto.connect_s3(aws_access_key_id, aws_secret_assess_key)
    bucket = connection.get_bucket(aws_bucket_name)

    filename = str(uuid.uuid4())
    content = json.dumps(data)

    key = Key(bucket, filename)
    key.set_contents_from_string(content)
    return filename
