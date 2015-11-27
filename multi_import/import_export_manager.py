from multi_import.exporter import Exporter
from multi_import.import_diff_applier import ImportDiffApplier
from multi_import.import_diff_generator import ImportDiffGenerator
from multi_import.serializers import SerializerFactory


class ImportExportManager(object):

    key = None
    model = None
    id_column = None
    lookup_fields = ('pk',)

    serializer = None

    exporter = Exporter
    import_diff_generator = ImportDiffGenerator
    import_diff_applier = ImportDiffApplier

    def __init__(self):
        self.serializer_factory = SerializerFactory(self.serializer)

    @property
    def dependencies(self):
        """
        Returns a list of related models that this importer is dependent on.
        """
        return self.serializer_factory.fields.dependencies

    def get_exporter_kwargs(self):
        return {
            'queryset': self.get_export_queryset(),
            'serializer_factory': self.serializer_factory
        }

    def get_exporter(self):
        return self.exporter(**self.get_exporter_kwargs())

    def get_import_diff_generator_kwargs(self):
        return {
            'key': self.key,
            'model': self.model,
            'lookup_fields': self.lookup_fields,
            'queryset': self.get_import_queryset(),
            'serializer_factory': self.serializer_factory
        }

    def get_import_diff_generator(self):
        return self.import_diff_generator(
            **self.get_import_diff_generator_kwargs()
        )

    def get_import_diff_applier_kwargs(self):
        return {
            'model': self.model,
            'queryset': self.get_import_queryset(),
            'serializer_factory': self.serializer_factory
        }

    def get_import_diff_applier(self):
        return self.import_diff_applier(
            **self.get_import_diff_applier_kwargs()
        )

    def get_queryset(self):
        queryset = self.model.objects
        fields = self.serializer_factory.fields

        for field in fields.related_fields():
            queryset = queryset.select_related(field.source)

        for field in fields.many_related_fields():
            queryset = queryset.prefetch_related(field.source)

        return queryset

    def get_export_queryset(self):
        return self.get_queryset()

    def get_import_queryset(self):
        return self.get_queryset()

    def export_dataset(self, template=False):
        exporter = self.get_exporter()
        return exporter.export_dataset(template)

    def generate_import_diff(self, dataset, new_object_refs):
        import_diff_generator = self.get_import_diff_generator()
        return import_diff_generator.generate_import_diff(dataset,
                                                          new_object_refs)

    def apply_import_diff(self, diff_data):
        import_diff_applier = self.get_import_diff_applier()
        return import_diff_applier.apply_diff(diff_data)
