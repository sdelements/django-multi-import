from exporter import Exporter
from import_diff_applier import ImportDiffApplier
from import_diff_generator import ImportDiffGenerator
from mappings import BoundMapping
from object_resolver import ObjectResolver
from value_resolver import ValueResolver


class ImportExportManager(object):

    key = None
    model = None
    id_column = None
    mappings = []
    lookup_fields = ('pk',)

    value_resolver = ValueResolver

    exporter = Exporter
    import_diff_generator = ImportDiffGenerator
    import_diff_applier = ImportDiffApplier

    def __init__(self):
        self.column_mappings = {}
        self.field_mappings = {}
        self.bind_mappings(list(self.mappings))

    def bind_mappings(self, mappings):
        self.mappings = [BoundMapping(mapping, self.model) for mapping in mappings]
        self.column_mappings = {mapping.column_name: mapping for mapping in self.mappings}
        self.field_mappings = {mapping.field_name: mapping for mapping in self.mappings}

    @property
    def writable_mappings(self):
        return [mapping for mapping in self.mappings if not mapping.readonly]

    @property
    def dependencies(self):
        """
        Returns a list of related models that this importer is dependent on.
        """
        return [mapping.related_model for mapping in self.writable_mappings if mapping.is_relationship]

    def get_value_resolver_kwargs(self):
        return {}

    def get_object_resolver(self):
        return ObjectResolver(self.value_resolver, self.mappings, self.get_value_resolver_kwargs())

    def get_exporter_kwargs(self):
        return {
            'mappings': self.mappings,
            'queryset': self.get_export_queryset(),
            'object_resolver': self.get_object_resolver()
        }

    def get_exporter(self):
        return self.exporter(**self.get_exporter_kwargs())

    def get_import_diff_generator_kwargs(self):
        return {
            'key': self.key,
            'model': self.model,
            'mappings': self.mappings,
            'field_mappings': self.field_mappings,
            'lookup_fields': self.lookup_fields,
            'queryset': self.get_import_queryset(),
            'object_resolver': self.get_object_resolver()
        }

    def get_import_diff_generator(self):
        return self.import_diff_generator(**self.get_import_diff_generator_kwargs())

    def get_import_diff_applier_kwargs(self):
        return {
            'model': self.model,
            'mappings': self.mappings,
            'queryset': self.get_import_queryset()
        }

    def get_import_diff_applier(self):
        return self.import_diff_applier(**self.get_import_diff_applier_kwargs())

    def get_queryset(self):
        queryset = self.model.objects

        for mapping in self.mappings:
            if mapping.is_foreign_key:
                queryset = queryset.select_related(mapping.field_name)
            elif mapping.is_one_to_many:
                queryset = queryset.prefetch_related(mapping.field_name)

        return queryset

    def get_export_queryset(self):
        return self.get_queryset()

    def get_import_queryset(self):
        return self.get_queryset()

    def export_dataset(self, template=False):
        exporter = self.get_exporter()
        return exporter.export_dataset(template)

    def generate_import_diff(self, dataset, new_object_refs=None):
        import_diff_generator = self.get_import_diff_generator()
        return import_diff_generator.generate_import_diff(dataset, new_object_refs)

    def apply_import_diff(self, diff_data):
        import_diff_applier = self.get_import_diff_applier()
        return import_diff_applier.apply_diff(diff_data)
