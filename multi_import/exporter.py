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
        return [
            field_name
            for field_name, field in self.serializer.get_fields().items()
            if not field.write_only
        ]

    def escape(self, s):
        """
        This escape method will prevent csv macro injection.
        When excel sees a space, it treats the contents as a string,
        therefore preventing formulas from running.
        """
        blacklist = ['=', '+', '-', '@']

        if s and s[0] in blacklist:
            s = ' ' + s

        return s

    def get_row(self, instance):
        results = []
        representation = self.serializer.to_representation(instance=instance)
        for column_name, value in representation.items():
            field = self.serializer.fields[column_name]
            results.append(
                self.escape(self.to_string_representation(field, value))
            )
        return results
