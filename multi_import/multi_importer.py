from django.db import transaction

from multi_import.importer import Result
from multi_import.object_cache import ObjectCache


class InvalidDatasetError(Exception):
    pass


class ImportInvalidError(Exception):
    pass


class MultiImportResult(object):
    """
    Results from an attempt to generate an import diff for several files.
    """
    def __init__(self):
        self.files = []
        self.errors = {}

    @property
    def valid(self):
        return len(self.errors) == 0

    def add_result(self, filename, result):
        if result.valid is False:
            self.errors[filename] = result.errors

        self.files.append({
            'filename': filename,
            'result': result
        })

    def add_error(self, filename, message):
        self.errors[filename] = [{'message': message}]

    def num_changes(self):
        return sum(
            len(file['result'].changes) for file in self.files
        )

    def has_changes(self):
        return any(file['result'].changes for file in self.files)

    def to_json(self):
        return {
            'files': [
                {
                    'filename': file['filename'],
                    'result': file['result'].to_json(),
                }
                for file in self.files
            ]
        }

    @classmethod
    def from_json(cls, data):
        result = cls()
        for file in data['files']:
            result.add_result(file['filename'],
                              Result.from_json(file['result']))
        return result


class ExportResult(object):
    """
    Results from an attempt to export multiple datasets.
    """
    def __init__(self):
        self.datasets = {}

    def add_result(self, key, dataset):
        self.datasets[key] = dataset


class MultiImportExporter(object):
    """
    Coordinates several ImportExporter classes,
    to enable multi-dataset export and imports.
    """
    classes = []

    error_messages = {
        'invalid_key': u'Columns should match those in the import template.',
        'invalid_export_keys': u'Invalid keys {0} for exporting'
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

    def import_data(self, data, commit=False):
        results = MultiImportResult()

        try:
            with transaction.atomic():
                context = {
                    'new_object_cache': self.get_new_object_cache()
                }

                bound_importers = self.transform_multi_input(data)

                for importer, filename, dataset in bound_importers:
                    result = importer.import_data(dataset, context)
                    results.add_result(filename, result)

                if not results.valid or not commit:
                    raise ImportInvalidError

        except ImportInvalidError:
            pass

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

        result = ExportResult()

        for exporter in exporters:
            dataset = exporter.export_dataset(template)
            result.add_result(exporter.key, dataset)

        return result
