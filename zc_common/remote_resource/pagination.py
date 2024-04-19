"""
Pagination fields

hamedahmadi 05/02/2016:
Had to create this custom pagination to include self link

see:
https://github.com/django-json-api/django-rest-framework-json-api/blob/develop/rest_framework_json_api/pagination.py
"""
from collections import OrderedDict

from six.moves.urllib import parse as urlparse
from rest_framework.pagination import PageNumberPagination as OldPagination
from rest_framework.views import Response


def remove_query_param(url, key):
    """
    Given a URL and a key/val pair, remove an item in the query
    parameters of the URL, and return the new URL.

    Forked from rest_framework.utils.urls; overwriten here because we
    need to pass keep_blank_values=True to urlparse.parse_qs() so that
    it doesn't remove the ?ifilter[id__in]= blank query parameter from
    our links in the case of an empty remote to-many link.
    """
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    query_dict = urlparse.parse_qs(query, keep_blank_values=True)
    query_dict.pop(key, None)
    query = urlparse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))


def replace_query_param(url, key, val):
    """
    Given a URL and a key/val pair, set or replace an item in the query
    parameters of the URL, and return the new URL.

    Forked from rest_framework.utils.urls; overwriten here because we
    need to pass keep_blank_values=True to urlparse.parse_qs() so that
    it doesn't remove the ?filter[id__in]= blank query parameter from
    our links in the case of an empty remote to-many link.
    """
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    query_dict = urlparse.parse_qs(query, keep_blank_values=True)
    query_dict[key] = [val]
    query = urlparse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))


class PageNumberPagination(OldPagination):
    """
    A json-api compatible pagination format
    """

    page_size_query_param = 'page_size'
    max_page_size = 1000

    def build_link(self, index):
        if not index:
            return None
        url = self.request and self.request.build_absolute_uri() or ''
        return replace_query_param(url, 'page', index)

    def get_paginated_response(self, data):
        next_page = None
        previous_page = None

        if self.page.has_next():
            next_page = self.page.next_page_number()
        if self.page.has_previous():
            previous_page = self.page.previous_page_number()

        # hamedahmadi 05/02/2016 -- Adding this to include self link
        self_url = remove_query_param(self.request.build_absolute_uri(), self.page_query_param)
        return Response({
            'results': data,
            'meta': {
                'pagination': OrderedDict([
                    ('page', self.page.number),
                    ('pages', self.page.paginator.num_pages),
                    ('count', self.page.paginator.count),
                ])
            },
            'links': OrderedDict([
                ('self', self_url),
                ('first', self.build_link(1)),
                ('last', self.build_link(self.page.paginator.num_pages)),
                ('next', self.build_link(next_page)),
                ('prev', self.build_link(previous_page))
            ])
        })
