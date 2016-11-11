from multi_import import serializers
from multi_import.exporter import Exporter
from multi_import.importer import Importer


class ImportExportManager(object):

    key = None
    model = None
    id_column = None
    lookup_fields = ('pk',)

    serializer = None

    exporter = Exporter
    importer = Importer

    @property
    def dependencies(self):
        """
        Returns a list of related models that this importer is dependent on.
        """
        return serializers.get_dependencies(self.serializer())

    def get_exporter_kwargs(self):
        return {
            'queryset': self.get_export_queryset(),
            'serializer': self.serializer
        }

    def get_exporter(self):
        return self.exporter(**self.get_exporter_kwargs())

    def get_importer_kwargs(self):
        return {
            'key': self.key,
            'model': self.model,
            'lookup_fields': self.lookup_fields,
            'queryset': self.get_import_queryset(),
            'serializer': self.serializer
        }

    def get_importer(self):
        return self.importer(
            **self.get_importer_kwargs()
        )

    def get_queryset(self):
        queryset = self.model.objects
        serializer = self.serializer()

        for field in serializers.get_related_fields(serializer):
            queryset = queryset.select_related(field.source)

        for field in serializers.get_many_related_fields(serializer):
            queryset = queryset.prefetch_related(field.source)

        return queryset

    def get_export_queryset(self):
        return self.get_queryset()

    def get_import_queryset(self):
        return self.get_queryset()

    def export_dataset(self, template=False):
        exporter = self.get_exporter()
        return exporter.export_dataset(template)

    def import_data(self, data, context=None):
        importer = self.get_importer()
        return importer.run(data, context)
