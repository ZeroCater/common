from datetime import date
import logging
import six
import time
import uuid

import boto
from boto.s3.key import Key
from django.conf import settings

logger = logging.getLogger('django')

S3_BUCKET_NAME = 'zc-mp-email'
EMAIL_EVENT_TYPE = 'send_email'
ATTACHMENT_PREFIX = 'attachment_'


class MissingCredentialsError(Exception):
    pass


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


def get_s3_email_bucket():
    aws_access_key_id = settings.AWS_ACCESS_KEY_ID
    aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
    if not (aws_access_key_id and aws_secret_access_key):
        msg = 'You need to set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your settings file.'
        raise MissingCredentialsError(msg)

    conn = boto.connect_s3(aws_access_key_id, aws_secret_access_key)
    bucket = conn.get_bucket(S3_BUCKET_NAME)
    return bucket


def generate_s3_folder_name(email_uuid):
    email_date = date.today().isoformat()
    email_timestamp = int(time.time())
    return "{}/{}_{}".format(email_date, email_timestamp, email_uuid)


def generate_s3_content_key(s3_folder_name, content_type, content_name=''):
    content_key = "{}/{}".format(s3_folder_name, content_type)
    if content_name:
        content_key += '_{}'.format(content_name)
    return content_key


def upload_string_to_s3(bucket, content_key, content):
    if content:
        k = Key(bucket)
        k.key = content_key
        k.set_contents_from_string(content)


def upload_file_to_s3(bucket, content_key, filename):
    if filename:
        k = Key(bucket)
        k.key = content_key
        k.set_contents_from_filename(filename)


def send_email(from_email=None, to=None, cc=None, bcc=None, reply_to=None,
               subject=None, plaintext_body=None, html_body=None, headers=None,
               files=None, attachments=None, user_id=None, resource_type=None, resource_id=None,
               logger=None):
    """
    files:       A list of file paths
    attachments: A list of tuples of the format (filename, content_type, content)
    """
    email_uuid = uuid.uuid4()
    bucket = get_s3_email_bucket()
    s3_folder_name = generate_s3_folder_name(email_uuid)
    if logger:
        msg = '''MICROSERVICE_SEND_EMAIL: Upload email with UUID {}, to {}, from {},
        with attachments {} and files {}'''
        logger.info(msg.format(email_uuid, to, from_email, attachments, files))

    to = to.split(',') if isinstance(to, six.string_types) else to
    cc = cc.split(',') if isinstance(cc, six.string_types) else cc
    bcc = bcc.split(',') if isinstance(bcc, six.string_types) else bcc
    reply_to = reply_to.split(',') if isinstance(reply_to, six.string_types) else reply_to
    for arg in (to, cc, bcc, reply_to):
        if arg and not isinstance(arg, list):
            msg = "Keyword arguments 'to', 'cc', 'bcc', and 'reply_to' should be of <type 'list'>"
            raise TypeError(msg)

    if not any([to, cc, bcc, reply_to]):
        msg = "Keyword arguments 'to', 'cc', 'bcc', and 'reply_to' can't all be empty"
        raise TypeError(msg)

    html_body_key = None
    if html_body:
        html_body_key = generate_s3_content_key(s3_folder_name, 'html')
        upload_string_to_s3(bucket, html_body_key, html_body)

    plaintext_body_key = None
    if plaintext_body:
        plaintext_body_key = generate_s3_content_key(s3_folder_name, 'plaintext')
        upload_string_to_s3(bucket, plaintext_body_key, plaintext_body)

    attachments_keys = []
    if attachments:
        for filename, mimetype, attachment in attachments:
            attachment_key = generate_s3_content_key(s3_folder_name, 'attachment',
                                                     content_name=filename)
            upload_string_to_s3(bucket, attachment_key, attachment)
            attachments_keys.append(attachment_key)
    if files:
        for filepath in files:
            filename = filepath.split('/')[-1]
            attachment_key = generate_s3_content_key(s3_folder_name, 'attachment',
                                                     content_name=filename)
            upload_file_to_s3(bucket, attachment_key, filepath)
            attachments_keys.append(attachment_key)

    event_data = {
        'from_email': from_email,
        'to': to,
        'cc': cc,
        'bcc': bcc,
        'reply_to': reply_to,
        'subject': subject,
        'plaintext_body_key': plaintext_body_key,
        'html_body_key': html_body_key,
        'attachments_keys': attachments_keys,
        'headers': headers,
        'user_id': user_id,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'task_id': str(email_uuid)
    }

    if logger:
        logger.info('MICROSERVICE_SEND_EMAIL: Sent email with UUID {} and data {}'.format(
            email_uuid, event_data
        ))

    emit_microservice_event(EMAIL_EVENT_TYPE, **event_data)
