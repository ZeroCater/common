"""
Class Mixins.
"""
from django.db import IntegrityError
from django.http import Http404


class MultipleIDMixin(object):
    """
    Override get_queryset for multiple id support
    """
    def get_queryset(self):
        """
        Override :meth:``get_queryset``
        """
        if hasattr(self.request, 'query_params'):
            ids = dict(self.request.query_params).getlist('ids[]')
            if ids:
                try:
                    self.queryset = self.queryset.filter(pk__in=ids)
                except (ValueError, IntegrityError):
                    raise Http404
        return self.queryset
