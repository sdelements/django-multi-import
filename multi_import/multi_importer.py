from django.utils.translation import ugettext_lazy as _

from multi_import.cache import ObjectCache
from multi_import.data import MultiExportResult, MultiImportResult
from multi_import.exceptions import InvalidDatasetError
from multi_import.helpers.transactions import transaction


class MultiImportExporter(object):
    """
    Coordinates several ImportExporter classes,
    to enable multi-dataset export and imports.
    """
    classes = []

    error_messages = {
        'invalid_key': _(
            u'Columns should match those in the import template.'
        ),
        'invalid_export_keys': _(u'Invalid keys {0} for exporting')
    }

    def __init__(self):
        import_export_managers = [
            cls(**self.get_import_export_manager_kwargs())
            for cls in self.classes
        ]
        self.import_export_managers = self.sort_importers(
            import_export_managers
        )

    def get_import_export_manager_kwargs(self):
        return {}

    def sort_importers(self, importers):
        """
        Sorts importers based on their inter-dataset dependencies.
        """
        results = []
        for importer in importers:
            if not len(importer.dependencies) > 0:
                index = 0
            else:
                models = [result.model for result in results]
                try:
                    index = 1 + max([
                        models.index(dependency)
                        for dependency in importer.dependencies
                    ])
                except ValueError:
                    index = -1

            if index == -1:
                results.append(importer)
            else:
                results.insert(index, importer)
        return results

    def identify_dataset(self, filename, dataset):
        models = (
            importer.model for importer in self.import_export_managers
            if importer.id_column in dataset.headers
        )
        model = next(models, None)
        if not model:
            raise InvalidDatasetError(self.error_messages['invalid_key'])

        return model, (filename, dataset)

    def get_new_object_cache(self):
        cache = {}
        for importer in self.import_export_managers:
            cache[importer.model] = ObjectCache(importer.lookup_fields)
        return cache

    def transform_multi_input(self, input_data):
        if isinstance(input_data, MultiImportResult):
            for importer in self.import_export_managers:
                datasets = (
                    f for f in input_data.files
                    if f['result'].key == importer.key
                )
                for dataset in datasets:
                    yield importer, dataset['filename'], dataset['result']
            return

        for importer in self.import_export_managers:
            for file_data in input_data.get(importer.model, []):
                filename, data = file_data
                yield importer, filename, data

    @transaction
    def import_data(self, data):
        results = MultiImportResult()

        context = {
            'new_object_cache': self.get_new_object_cache()
        }

        bound_importers = self.transform_multi_input(data)

        for importer, filename, dataset in bound_importers:
            result = importer.import_data(dataset, context, transaction=False)
            results.add_result(filename, result)

        return results

    def export_datasets(self, keys=None, template=False):
        if keys:
            # Check to make sure we're not passing in bad keys
            all_valid_keys = [
                exporter.key for exporter in self.import_export_managers
            ]
            invalid_keys = [key for key in keys if key not in all_valid_keys]
            if invalid_keys:
                error_key = 'invalid_export_keys'
                joined_keys = ','.join(invalid_keys)
                raise ValueError(
                    self.error_messages[error_key].format(joined_keys)
                )

            exporters = [
                exporter for exporter in self.import_export_managers
                if exporter.key in keys
            ]
        else:
            exporters = self.import_export_managers

        result = MultiExportResult()

        for exporter in exporters:
            dataset = exporter.export_dataset(template)
            result.add_result(exporter.key, dataset)

        return result
