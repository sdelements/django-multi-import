class ResolvedObject(object):
    """
    A set of resolved values.
    """
    def __init__(self, values):
        self.dict = dict(values)
        self.list = [value[1] for value in values]

    @property
    def errors(self):
        return [
            (value.mapping, value.errors) for value in self.list
            if value.errors
        ]


class ObjectResolver(object):
    """
    Resolves an object - a set of values (using many ValueResolver objects).
    """
    def __init__(self, value_resolver, mappings, value_resolver_kwargs=None):
        self.value_resolver = value_resolver
        self.mappings = mappings
        self.value_resolver_kwargs = value_resolver_kwargs or {}

    def get_value_resolver(self, mapping):
        return self.value_resolver(mapping=mapping,
                                   **self.value_resolver_kwargs)

    def get_value_resolvers(self, columns=None):
        if columns:
            mappings = self.mappings.filter_by_columns(columns)
        else:
            mappings = self.mappings

        return [self.get_value_resolver(mapping) for mapping in mappings]

    def resolve_export_values(self, instance, columns=None):
        value_resolvers = self.get_value_resolvers(columns)
        resolved_values = [
            (value_resolver.mapping.field_name,
             value_resolver.resolve_export_value(instance))
            for value_resolver in value_resolvers
        ]
        return ResolvedObject(resolved_values)

    def resolve_import_values(self,
                              source,
                              new_object_refs=None,
                              columns=None):

        value_resolvers = self.get_value_resolvers(columns)
        resolved_values = [
            (value_resolver.mapping.field_name,
             value_resolver.resolve_import_value(source, new_object_refs))
            for value_resolver in value_resolvers
        ]
        return ResolvedObject(resolved_values)
