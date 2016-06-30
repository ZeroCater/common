import json
import requests
from inflection import underscore
from uritemplate import expand

from zc_common.jwt_auth.utils import service_jwt_payload_handler, jwt_encode_handler
from zc_common.settings import zc_settings


# Requests that can be made to another service
HTTP_GET = 'get'
HTTP_POST = 'post'


class UnsupportedHTTPMethodException(Exception):
    pass


class RouteNotFoundException(Exception):
    pass


class ServiceRequestException(Exception):
    pass


class RemoteResourceException(Exception):
    pass


class RemoteResourceWrapper(object):

    def __init__(self, data):
        self.data = data
        self.create_properties_from_data()

    def create_properties_from_data(self):
        if 'id' in self.data:
            setattr(self, 'id', self.data.get('id'))

        if 'type' in self.data:
            setattr(self, 'type', self.data.get('type'))

        if 'attributes' in self.data:
            attributes = self.data['attributes']
            for key in attributes.keys():
                setattr(self, underscore(key), attributes[key])

        if 'relationships' in self.data:
            relationships = self.data['relationships']

            for key in relationships.keys():
                if isinstance(relationships[key]['data'], list):
                    setattr(self, underscore(key), RemoteResourceListWrapper(relationships[key]['data']))
                else:
                    setattr(self, underscore(key), RemoteResourceWrapper(relationships[key]['data']))


class RemoteResourceListWrapper(list):
    def __init__(self, data):
        self.data = data
        self.add_items_from_data()

    def add_items_from_data(self):
        map(lambda x: self.append(RemoteResourceWrapper(x)), self.data)


def get_route_from_fk(resource_type, pk=None):
    """Gets a fully qualified URL for a given resource_type, pk"""
    routes = requests.get(zc_settings.GATEWAY_ROOT_PATH).json()

    for route in routes.iterkeys():
        if 'resource_type' in routes[route] and routes[route]['resource_type'] == resource_type:
            if isinstance(pk, (list, set)):
                expanded = '{}?filter[id__in]={}'.format(expand(route, {}), ','.join([str(x) for x in pk]))
            else:
                expanded = expand(route, {'id': pk})
            return '{0}{1}'.format(routes[route]['domain'], expanded)

    raise RouteNotFoundException('No route for resource_type: "{0}"'.format(resource_type))


def make_service_request(service_name, endpoint, method=HTTP_GET, data=None):
    """
    Makes a JWT token-authenticated service request to the URL provided.

    Args:
        service_name: name of the service making this request. e.g. mp-users
        endpoint: the url to use
        method: HTTP method. supported methods are defined at this module's global variables
        data: request payload in case we are making a POST request

    Returns: text content of the response
    """

    jwt_token = jwt_encode_handler(service_jwt_payload_handler(service_name))
    headers = {'Authorization': 'JWT {}'.format(jwt_token), 'Content-Type': 'application/vnd.api+json'}

    if method == HTTP_GET:
        response = requests.get(endpoint, headers=headers)
    elif method == HTTP_POST:
        response = requests.post(endpoint, json=data, headers=headers)
    else:
        raise UnsupportedHTTPMethodException(
            "Method {0} is not supported. service_name: {1}, endpoint: {2}".format(method, service_name, endpoint))

    if 400 <= response.status_code < 600:
        http_error_msg = '{0} Error: {1} for url: {2}. Content: {3}'.format(
            response.status_code, response.reason, response.url, response.text)
        raise ServiceRequestException(http_error_msg)

    return response.text


def get_remote_resource(service_name, resource_type, pk):
    """A shortcut function to make a GET request to a remote service."""
    url = get_route_from_fk(resource_type, pk)
    response = make_service_request(service_name, url)
    json_response = json.loads(response)

    if 'data' in json_response:
        resource_data = json_response['data']
        if isinstance(resource_data, list):
            return RemoteResourceListWrapper(resource_data)
        return RemoteResourceWrapper(resource_data)

    msg = "Error retrieving resource. service_name: {0}, resource_type: {1}, pk: {2}, " \
          "response: {3}".format(service_name, resource_type, pk, response)
    raise RemoteResourceException(msg)
