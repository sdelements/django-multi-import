from django.utils.translation import gettext_lazy as _

from multi_import.data import MultiExportResult, MultiImportResult
from multi_import.exceptions import InvalidDatasetError, InvalidFileError
from multi_import.formats import all_formats, supported_mimetypes
from multi_import.helpers import files as file_helper
from multi_import.helpers.transactions import transaction


class MultiImporter(object):
    """
    Coordinates several ImportExporter classes,
    to enable multi-dataset export and imports.
    """

    importers = []
    file_formats = all_formats
    mimetypes = supported_mimetypes
    export_filename = "export"

    error_messages = {
        "invalid_key": _("Columns should match those in the import template."),
        "invalid_export_keys": _("Invalid keys {0} for exporting"),
    }

    def __init__(self):
        import_export_managers = [
            cls(**self.get_importer_kwargs()) for cls in self.importers
        ]
        self.importer_instances = self._sort_importers(import_export_managers)

    def get_export_filename(self):
        return self.export_filename

    def get_importer_kwargs(self):
        return {}

    def export(self, empty=False, keys=None):
        exporters = self._get_exporters(keys)

        results = tuple(exporter.export(empty=empty) for exporter in exporters)

        return MultiExportResult(
            filename=self.get_export_filename(),
            file_formats=self.file_formats,
            results=results,
        )

    @transaction
    def import_files(self, files):
        results = MultiImportResult()

        data = {}
        for filename, file in files.items():
            try:
                if file.content_type not in self.mimetypes:
                    msg = (
                        "{} file types are not supported. Please upload a .csv"
                        " or .xslx file.".format(file.content_type)
                    )
                    raise InvalidFileError(msg)

                dataset = file_helper.read(self.file_formats, file)
                import_key, data_item = self._identify_dataset(filename, dataset)
                if import_key in data:
                    data[import_key].append(data_item)
                else:
                    data[import_key] = [data_item]
            except (InvalidDatasetError, InvalidFileError) as e:
                results.add_error(filename, str(e))

        if not results.valid:
            return results

        return self.import_data(data, transaction=False)

    @transaction
    def import_data(self, data):
        results = MultiImportResult()

        context = {
            "model_contexts": {
                importer.model: importer.get_model_context()
                for importer in self.importer_instances
            }
        }

        bound_importers = self._transform_multi_input(data)

        read_datasets = []

        for importer, datasets in bound_importers:
            serializer_context = importer.get_import_serializer_context(context)

            read_datasets.extend(
                [
                    (
                        importer,
                        importer.read_rows(dataset),
                        filename,
                        serializer_context,
                    )
                    for filename, dataset in datasets
                ]
            )

        max_steps = max(
            len(importer.get_serializer_classes())
            for importer, _rows, _filename, serializer_context in read_datasets
        )

        for importer, rows, _filename, serializer_context in read_datasets:
            importer.load_instances(rows, serializer_context)

        for step in range(max_steps):
            for importer, rows, _filename, serializer_context in read_datasets:
                importer.process_rows(rows, serializer_context, step)

        for importer, rows, _filename, _serializer_context in read_datasets:
            importer.validate_rows_post_save(rows)

        for importer, rows, _filename, _serializer_context in read_datasets:
            importer.process_diffs(rows)

        for importer, rows, filename, _serializer_context in read_datasets:
            result = importer.transform_rows_to_result(rows)
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
                    index = 1 + max(
                        [
                            models.index(dependency)
                            for dependency in importer.dependencies
                        ]
                    )
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
        all_valid_keys = [exporter.key for exporter in self.importer_instances]
        invalid_keys = [key for key in keys if key not in all_valid_keys]
        if invalid_keys:
            error_key = "invalid_export_keys"
            joined_keys = ",".join(invalid_keys)
            raise ValueError(self.error_messages[error_key].format(joined_keys))

        return (
            exporter for exporter in self.importer_instances if exporter.key in keys
        )

    def _identify_dataset(self, filename, dataset):
        importer_keys = (
            importer.key
            for importer in self.importer_instances
            if dataset.headers and importer.id_column in dataset.headers
        )
        key = next(importer_keys, None)
        if not key:
            raise InvalidDatasetError(self.error_messages["invalid_key"])

        return key, (filename, dataset)

    def _transform_multi_input(self, input_data):
        for importer in self.importer_instances:
            if isinstance(input_data, MultiImportResult):
                datasets = [
                    (f["filename"], f["result"])
                    for f in input_data.files
                    if f["result"].key == importer.key
                ]
            else:
                datasets = input_data.get(importer.key)

            if datasets:
                yield (importer, datasets)
