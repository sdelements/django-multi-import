from multi_import.exporter import Exporter
from multi_import.import_behaviours import (ImportDiffApplier,
                                            ImportDiffGenerator)
from multi_import.importer import Importer


class ImportExportManager(object):

    key = None
    model = None
    id_column = None
    lookup_fields = ('pk',)

    serializer = None

    exporter = Exporter
    importer = Importer
    import_diff_generator = ImportDiffGenerator
    import_diff_applier = ImportDiffApplier

    @property
    def dependencies(self):
        """
        Returns a list of related models that this importer is dependent on.
        """
        return self.serializer().dependencies

    def get_exporter_kwargs(self):
        return {
            'queryset': self.get_export_queryset(),
            'serializer': self.serializer
        }

    def get_exporter(self):
        return self.exporter(**self.get_exporter_kwargs())

    def get_importer_kwargs(self, import_behaviour):
        return {
            'import_behaviour': import_behaviour,
            'key': self.key,
            'model': self.model,
            'lookup_fields': self.lookup_fields,
            'queryset': self.get_import_queryset(),
            'serializer': self.serializer
        }

    def get_importer(self, import_behaviour):
        return self.importer(
            **self.get_importer_kwargs(import_behaviour)
        )

    def get_queryset(self):
        queryset = self.model.objects
        serializer = self.serializer()

        for field in serializer.related_fields():
            queryset = queryset.select_related(field.source)

        for field in serializer.many_related_fields():
            queryset = queryset.prefetch_related(field.source)

        return queryset

    def get_export_queryset(self):
        return self.get_queryset()

    def get_import_queryset(self):
        return self.get_queryset()

    def export_dataset(self, template=False):
        exporter = self.get_exporter()
        return exporter.export_dataset(template)

    def generate_import_diff(self, dataset, context=None):
        importer = self.get_importer(self.import_diff_generator)
        return importer.run(dataset, context)

    def apply_import_diff(self, diff_data, context=None):
        importer = self.get_importer(self.import_diff_applier)
        return importer.run(diff_data, context)
