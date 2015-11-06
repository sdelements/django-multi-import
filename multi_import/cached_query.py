from collections import defaultdict


class CachedQuery(defaultdict):
    def __init__(self, queryset, lookup_fields):
        super(CachedQuery, self).__init__(self.default_factory)
        self.queried = False
        self.queryset = queryset
        self.lookup_fields = lookup_fields

    def default_factory(self):
        return defaultdict(set)

    def add_lookup_value(self, field, value, instance):
        if not value:
            return

        lookup_dict = self[field]
        key = str(value)

        lookup_dict[key].add(instance)

    def get_lookup_value(self, field, value):
        if field not in self or value is None:
            return None

        lookup_dict = self[field]
        key = str(value)

        instance_set = lookup_dict[key]
        if not instance_set:
            return None

        if len(instance_set) > 1:
            return self.queryset.model.MultipleObjectsReturned

        return next(iter(instance_set))

    def cache_instance(self, instance):
        for field in self.lookup_fields:
            value = getattr(instance, field, None)
            self.add_lookup_value(field, value, instance)

    def execute_query(self):
        for instance in self.queryset:
            self.cache_instance(instance)
        self.queried = True

    def ensure_queried(self):
        if not self.queried:
            self.execute_query()

    def get(self, field, value, default=None):
        self.ensure_queried()
        return self.get_lookup_value(field, value) or default

    def lookup(self, fields, data):
        self.ensure_queried()
        for field in fields:
            value = data.get(field, None)
            result = self.get_lookup_value(field, value)
            if result:
                return result
        return None
