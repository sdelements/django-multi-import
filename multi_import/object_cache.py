from collections import defaultdict

from django.core.exceptions import MultipleObjectsReturned
import six
from tablib.compat import unicode


__all__ = [
    'ObjectCache',
    'CachedQuery',
]


class CachedObject(object):

    def __init__(self, obj):
        self.obj = obj

    def __hash__(self):
        if hasattr(self.obj, 'pk') and not getattr(self.obj, 'pk', None):
            return super(CachedObject, self).__hash__()
        return self.obj.__hash__()


class ObjectCache(defaultdict):
    multiple_objects_error = MultipleObjectsReturned

    def __init__(self, lookup_fields):
        super(ObjectCache, self).__init__(self._default_factory)
        self.lookup_fields = lookup_fields
        self.cached_object_count = 0

    def _default_factory(self):
        return defaultdict(set)

    def _add_lookup_value(self, field, value, cached_object):
        if not value:
            return

        lookup_dict = self[field]
        key = unicode(value)

        lookup_dict[key].add(cached_object)

    def _check_instance_set(self, instance_set):
        if len(instance_set) > 1:
            raise self.multiple_objects_error
        return None

    def _get_lookup_value(self, field, value):
        if isinstance(field, six.string_types):
            field = (field,)
            value = (value,)

        zipped_values = list(zip(field, value))

        for f, v in zipped_values:
            if f not in self or v is None:
                return None

        instance_sets = [
            self[f][unicode(v)]
            for f, v in zipped_values
        ]

        for s in instance_sets:
            if not s:
                return None

        instance_set = set.intersection(*instance_sets)

        if not instance_set:
            return None

        result = self._check_instance_set(instance_set)
        if result:
            return result

        return next(iter(instance_set)).obj

    def cache_instance(self, instance):
        fields_to_cache = set(
            item for sublist in
            (
                (fields,) if isinstance(fields, six.string_types) else fields
                for fields in self.lookup_fields
            )
            for item in sublist
        )

        cached_instance = CachedObject(instance)

        for field in fields_to_cache:
            value = getattr(instance, field, None)
            self._add_lookup_value(field, value, cached_instance)

        self.cached_object_count += 1

    def get(self, field, value, default=None):
        return self._get_lookup_value(field, value) or default

    def lookup_value(self, value):
        for field in self.lookup_fields:
            result = self._get_lookup_value(field, value)
            if result:
                return result
        return None

    def lookup(self, fields, data):
        for field in fields:
            if isinstance(field, six.string_types):
                value = data.get(field, None)
            else:
                value = [data.get(f) for f in field]
            result = self._get_lookup_value(field, value)
            if result:
                return result
        return None

    def __len__(self):
        return self.cached_object_count


class CachedQuery(ObjectCache):
    def __init__(self, queryset, lookup_fields):
        super(CachedQuery, self).__init__(lookup_fields)
        self.queried = False
        self.queryset = queryset
        self.multiple_objects_error = queryset.model.MultipleObjectsReturned

    def execute_query(self):
        for instance in self.queryset:
            self.cache_instance(instance)
        self.queried = True

    def ensure_queried(self):
        if not self.queried:
            self.execute_query()

    def get(self, field, value, default=None):
        self.ensure_queried()
        return super(CachedQuery, self).get(field, value, default)

    def lookup(self, fields, data):
        self.ensure_queried()
        return super(CachedQuery, self).lookup(fields, data)
