from django.db import transaction

from multi_import import import_behaviours
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
        self.diff = {
            'files': []
        }
        self.errors = {}

    @property
    def valid(self):
        return len(self.errors) == 0

    def add_result(self, filename, result):
        if result.valid is False:
            self.errors[filename] = result.errors

        diff = result.result.copy()
        diff['filename'] = filename
        self.diff['files'].append(diff)

    def add_error(self, filename, message):
        self.errors[filename] = [{'message': message}]


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

    standard_import_behaviour = import_behaviours.StandardImportBehaviour
    import_diff_generator = import_behaviours.GenerateDiffBehaviour
    import_diff_applier = import_behaviours.ApplyDiffBehaviour

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

    def import_data(self, data, import_behaviour=None):
        if import_behaviour is None:
            import_behaviour = self.standard_import_behaviour

        results = MultiImportResult()

        try:
            with transaction.atomic():
                context = {
                    'new_object_cache': self.get_new_object_cache()
                }

                bound_importers = import_behaviour.transform_multi_input(
                    self.import_export_managers, data
                )

                for importer, filename, dataset in bound_importers:
                    result = importer.import_data(
                        import_behaviour, dataset, context
                    )
                    results.add_result(filename, result)

                if not results.valid or not import_behaviour.save_changes:
                    raise ImportInvalidError

        except ImportInvalidError:
            pass

        return results

    def diff_generate(self, data):
        return self.import_data(data, self.import_diff_generator)

    def diff_apply(self, diff_data):
        return self.import_data(diff_data, self.import_diff_applier)

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
