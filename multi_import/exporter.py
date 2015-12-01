import tablib


class Exporter(object):

    def __init__(self, queryset, serializer_factory):
        self.queryset = queryset
        self.serializer = serializer_factory.default

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
        for column_name, value in representation.iteritems():
            field = self.serializer.fields[column_name]
            results.append(
                field.to_string_representation(value)
            )
        return results
