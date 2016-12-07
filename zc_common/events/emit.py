from __future__ import division

import logging
import uuid
import math

from django.conf import settings
from zc_common.events.utils import event_payload, save_to_s3file


logger = logging.getLogger('django')


class EmitEventException(Exception):
    pass


def emit_microservice_event(event_type, *args, **kwargs):
    import pika
    import ujson

    url = settings.BROKER_URL

    params = pika.URLParameters(url)
    params.socket_timeout = 5

    event_queue_name = '{}-events'.format(settings.SERVICE_NAME)

    connection = pika.BlockingConnection(params)

    channel = connection.channel()
    channel.queue_declare(queue=event_queue_name, durable=True)

    task_id = str(uuid.uuid4())

    keyword_args = {'task_id': task_id}
    keyword_args.update(kwargs)

    message = {
        'task': 'microservice.event',
        'id': task_id,
        'args': [event_type] + list(args),
        'kwargs': keyword_args
    }

    event_body = ujson.dumps(message)

    logger.info('MICROSERVICE_EVENT::EMIT: Emitting [{}:{}] event for object ({}:{}) and user {}'.format(
        event_type, task_id, kwargs.get('resource_type'), kwargs.get('resource_id'),
        kwargs.get('user_id')))

    response = channel.basic_publish('microservice-events', '', event_body, pika.BasicProperties(
        content_type='application/json', content_encoding='utf-8'))

    if not response:
        logger.info(
            'MICROSERVICE_EVENT::EMIT_FAILURE: Failure emitting [{}:{}] event for object ({}:{}) and user {}'.format(
                event_type, task_id, kwargs.get('resource_type'), kwargs.get('resource_id'), kwargs.get('user_id')))
        raise EmitEventException("Message may have failed to deliver")

    return response


def emit_index_rebuild_event(event_name, resource_type, model, batch_size, serializer, queryset=None):
    """
    A special helper method to emit events related to index_rebuilding.

    Note: AWS_INDEXER_BUCKET_NAME must be present in your settings.
    """

    if queryset is None:
        queryset = model.objects.all()

    objects_count = queryset.count()
    total_events_count = int(math.ceil(objects_count / batch_size))
    emitted_events_count = 0

    while emitted_events_count < total_events_count:
        start_index = emitted_events_count * batch_size
        end_index = start_index + batch_size
        data = []

        for instance in queryset.order_by('id')[start_index:end_index]:
            instance_data = serializer(instance)
            data.append(instance_data)

        filename = save_to_s3file(data, settings.AWS_INDEXER_BUCKET_NAME)
        payload = event_payload(resource_type=resource_type, resource_id=None, user_id=None, meta={'s3_key': filename})
        emit_microservice_event(event_name, **payload)
        emitted_events_count += 1
