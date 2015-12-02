from multi_import.object_cache import ObjectCache


class InvalidDatasetError(Exception):
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

    def __init__(self):
        import_exporters = [
            cls(**self.get_import_export_manager_kwargs())
            for cls in self.classes
        ]
        self.import_exporters = self.sort_importers(import_exporters)

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
            importer.model for importer in self.import_exporters
            if importer.id_column in dataset.headers
        )
        model = next(models, None)
        if not model:
            raise InvalidDatasetError(self.error_messages['invalid_key'])

        return model, (filename, dataset)

    def get_new_object_cache(self):
        cache = {}
        for importer in self.import_exporters:
            cache[importer.model] = ObjectCache(importer.lookup_fields)
        return cache

    def import_datasets(self, datasets):
        results = MultiImportResult()

        context = {
            'new_object_cache': self.get_new_object_cache()
        }

        for importer in self.import_exporters:
            for file_data in datasets.get(importer.model, []):
                filename, data = file_data
                result = importer.generate_import_diff(data, context)
                results.add_result(filename, result)

        return results

    def apply_import(self, diff):
        files = diff.get('files', [])

        context = {
            'new_object_cache': self.get_new_object_cache()
        }

        for importer in self.import_exporters:
            datasets = (f for f in files if f['model'] == importer.key)
            for dataset in datasets:
                importer.apply_import_diff(dataset, context)

    def export_datasets(self, keys=None, template=False):
        if keys:
            # Check to make sure we're not passing in bad keys
            all_valid_keys = [
                exporter.key for exporter in self.import_exporters
            ]
            invalid_keys = [key for key in keys if key not in all_valid_keys]
            if invalid_keys:
                error_key = 'invalid_export_keys'
                joined_keys = ','.join(invalid_keys)
                raise ValueError(
                    self.error_messages[error_key].format(joined_keys)
                )

            exporters = [
                exporter for exporter in self.import_exporters
                if exporter.key in keys
            ]
        else:
            exporters = self.import_exporters

        result = ExportResult()

        for exporter in exporters:
            dataset = exporter.export_dataset(template)
            result.add_result(exporter.key, dataset)

        return result
