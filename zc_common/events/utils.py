
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
