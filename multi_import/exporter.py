import tablib


class Exporter(object):

    def __init__(self, mappings, queryset, object_resolver):
        self.mappings = mappings
        self.queryset = queryset
        self.object_resolver = object_resolver

    def export_dataset(self, template=False):
        dataset = tablib.Dataset(headers=self.get_header())

        if not template:
            for instance in self.queryset:
                dataset.append(self.get_row(instance))

        return dataset

    def get_header(self):
        return [mapping.column_name for mapping in self.mappings]

    def get_row(self, instance):
        resolved_values = self.object_resolver.resolve_export_values(instance)
        return [
            resolved_value.get_string()
            for resolved_value in resolved_values.list
        ]
