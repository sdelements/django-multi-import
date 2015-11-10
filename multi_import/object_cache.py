from collections import defaultdict

from django.core.exceptions import MultipleObjectsReturned


class ObjectCache(defaultdict):
    multiple_objects_error = MultipleObjectsReturned

    def __init__(self, lookup_fields):
        super(ObjectCache, self).__init__(self.default_factory)
        self.lookup_fields = lookup_fields
        self.cached_object_count = 0

    def default_factory(self):
        return defaultdict(set)

    def add_lookup_value(self, field, value, instance):
        if not value:
            return

        lookup_dict = self[field]
        key = unicode(value)

        lookup_dict[key].add(instance)

    def get_lookup_value(self, field, value):
        if field not in self or value is None:
            return None

        lookup_dict = self[field]
        key = unicode(value)

        instance_set = lookup_dict[key]
        if not instance_set:
            return None

        if len(instance_set) > 1:
            raise self.multiple_objects_error

        return next(iter(instance_set))

    def cache_instance(self, instance):
        for field in self.lookup_fields:
            value = getattr(instance, field, None)
            self.add_lookup_value(field, value, instance)
        self.cached_object_count += 1

    def get(self, field, value, default=None):
        return self.get_lookup_value(field, value) or default

    def lookup_value(self, value):
        for field in self.lookup_fields:
            result = self.get_lookup_value(field, value)
            if result:
                return result
        return None

    def lookup(self, fields, data):
        for field in fields:
            value = data.get(field, None)
            result = self.get_lookup_value(field, value)
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
