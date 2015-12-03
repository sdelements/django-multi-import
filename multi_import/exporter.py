import tablib

from multi_import.fields import FieldHelper

__all__ = [
    'Exporter',
]


class Exporter(FieldHelper):

    def __init__(self, queryset, serializer):
        self.queryset = queryset
        self.serializer = serializer()

    def export_dataset(self, template=False):
        dataset = tablib.Dataset(headers=self.get_header())

        if not template:
            for instance in self.queryset:
                dataset.append(self.get_row(instance))

        return dataset

    def get_header(self):
        return self.serializer.get_fields().keys()

    def get_row(self, instance):
        results = []
        representation = self.serializer.to_representation(instance=instance)
        for column_name, value in representation.items():
            field = self.serializer.fields[column_name]
            results.append(
                self.to_string_representation(field, value)
            )
        return results
