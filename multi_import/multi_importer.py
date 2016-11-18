from django.utils.translation import ugettext_lazy as _

from multi_import.cache import ObjectCache
from multi_import.data import MultiExportResult, MultiImportResult
from multi_import.exceptions import InvalidDatasetError, InvalidFileError
from multi_import.formats import all_formats
from multi_import.helpers import files as file_helper
from multi_import.helpers.transactions import transaction


class MultiImporter(object):
    """
    Coordinates several ImportExporter classes,
    to enable multi-dataset export and imports.
    """
    importers = []
    file_formats = all_formats
    export_filename = 'export'

    error_messages = {
        'invalid_key': _(
            u'Columns should match those in the import template.'
        ),
        'invalid_export_keys': _(u'Invalid keys {0} for exporting')
    }

    def __init__(self):
        import_export_managers = [
            cls(**self.get_importer_kwargs())
            for cls in self.importers
        ]
        self.importer_instances = self._sort_importers(
            import_export_managers
        )

    def get_export_filename(self):
        return self.export_filename

    def get_importer_kwargs(self):
        return {}

    def export(self, empty=False, keys=None):
        exporters = self._get_exporters(keys)

        results = tuple(
            exporter.export(empty=empty) for exporter in exporters
        )

        return MultiExportResult(
            filename=self.get_export_filename(),
            file_formats=self.file_formats,
            results=results
        )

    @transaction
    def import_files(self, files):
        results = MultiImportResult()

        data = {}
        for filename, file in files.items():
            try:
                dataset = file_helper.read(self.file_formats, file)
                model, data_item = self._identify_dataset(filename, dataset)
                if model in data:
                    data[model].append(data_item)
                else:
                    data[model] = [data_item]
            except(InvalidDatasetError, InvalidFileError) as e:
                results.add_error(filename, e.message)

        if not results.valid:
            return results

        return self.import_data(data, transaction=False)

    @transaction
    def import_data(self, data):
        results = MultiImportResult()

        context = {
            'new_object_cache': self._get_new_object_cache()
        }

        bound_importers = self._transform_multi_input(data)

        for importer, filename, dataset in bound_importers:
            result = importer.import_data(dataset, context, transaction=False)
            results.add_result(filename, result)

        return results

    def _sort_importers(self, importers):
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

    def _get_exporters(self, keys=None):
        if not keys:
            return self.importer_instances

        # Check to make sure we're not passing in bad keys
        all_valid_keys = [
            exporter.key for exporter in self.importer_instances
        ]
        invalid_keys = [key for key in keys if key not in all_valid_keys]
        if invalid_keys:
            error_key = 'invalid_export_keys'
            joined_keys = ','.join(invalid_keys)
            raise ValueError(
                self.error_messages[error_key].format(joined_keys)
            )

        return (
            exporter for exporter in self.importer_instances
            if exporter.key in keys
        )

    def _identify_dataset(self, filename, dataset):
        models = (
            importer.model for importer in self.importer_instances
            if importer.id_column in dataset.headers
        )
        model = next(models, None)
        if not model:
            raise InvalidDatasetError(self.error_messages['invalid_key'])

        return model, (filename, dataset)

    def _get_new_object_cache(self):
        cache = {}
        for importer in self.importer_instances:
            cache[importer.model] = ObjectCache(importer.lookup_fields)
        return cache

    def _transform_multi_input(self, input_data):
        if isinstance(input_data, MultiImportResult):
            for importer in self.importer_instances:
                datasets = (
                    f for f in input_data.files
                    if f['result'].key == importer.key
                )
                for dataset in datasets:
                    yield importer, dataset['filename'], dataset['result']
            return

        for importer in self.importer_instances:
            for file_data in input_data.get(importer.model, []):
                filename, data = file_data
                yield importer, filename, data
