from collections import defaultdict

from django.core.exceptions import MultipleObjectsReturned
import six
from tablib.compat import unicode


class CachedObject(object):

    def __init__(self, obj):
        self.obj = obj

    def __hash__(self):
        if hasattr(self.obj, 'pk') and not getattr(self.obj, 'pk', None):
            return super(CachedObject, self).__hash__()
        return self.obj.__hash__()


class ObjectCache(object):
    multiple_objects_error = MultipleObjectsReturned

    def __init__(self, lookup_fields):
        self.cache_fields = self._flatten_fields(lookup_fields)
        self.lookup_fields = lookup_fields
        self.object_count = 0
        self.objects = defaultdict(lambda: defaultdict(set))

    def __len__(self):
        return self.object_count

    def add(self, obj):
        cached_obj = CachedObject(obj)

        fields_to_cache = (
            (field, value)
            for field, value in
            (
                (field, getattr(obj, field, None))
                for field in self.cache_fields
            )
            if value is not None
        )

        for field, value in fields_to_cache:
            self.objects[field][unicode(value)].add(cached_obj)

        self.object_count += 1

    def get(self, field, value, default=None):
        if isinstance(field, six.string_types):
            field = (field,)
            value = (value,)

        zipped_values = list(zip(field, value))

        if any(f not in self.objects or v is None for f, v in zipped_values):
            return default

        result_sets = [
            self.objects[f][unicode(v)]
            for f, v in zipped_values
        ]

        results = [
            result.obj
            for result in set.intersection(*result_sets)
        ]

        return self.to_result(results) or default

    def find(self, value, fields=None):
        fields = fields or self.lookup_fields
        single_fields = (
            field for field in fields if isinstance(field, six.string_types)
        )
        for field in single_fields:
            result = self.get(field, value)
            if result:
                return result
        return None

    def match(self, data, fields=None):
        fields = fields or self.lookup_fields
        for field in fields:
            if isinstance(field, six.string_types):
                value = data.get(field, None)
            else:
                value = [data.get(f) for f in field]
            result = self.get(field, value)
            if result:
                return result
        return None

    def to_result(self, results):
        if len(results) > 1:
            raise self.multiple_objects_error

        return next(iter(results), None)

    def _flatten_fields(self, fields):
        return set(
            item for sublist in
            (
                (item,) if isinstance(item, six.string_types) else item
                for item in fields
            )
            for item in sublist
        )


class CachedQuery(ObjectCache):
    def __init__(self, queryset, lookup_fields):
        super(CachedQuery, self).__init__(lookup_fields)
        self.queried = False
        self.queryset = queryset
        self.multiple_objects_error = queryset.model.MultipleObjectsReturned

    def get(self, field, value, default=None):
        self._ensure_queried()
        return super(CachedQuery, self).get(field, value, default)

    def _ensure_queried(self):
        if self.queried:
            return

        for instance in self.queryset:
            self.add(instance)
        self.queried = True
