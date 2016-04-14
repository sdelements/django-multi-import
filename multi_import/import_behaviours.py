from six import string_types
from tablib.compat import unicode

from multi_import.fields import FieldHelper
from multi_import.import_result import ImportResult
from multi_import.utils import normalize_string


def normalize_row_data(row_data):
    """
    Converts all values in row_data dict to strings.
    Required for Excel imports.
    """
    data = {}
    for key, value in row_data.items():
        if value is None:
            value = ''

        if isinstance(value, float) and value.is_integer():
            value = int(value)

        if not isinstance(value, string_types):
            value = unicode(value)

        data[key] = normalize_string(value)
    return data


__all__ = [
    'BaseImportBehaviour',
    'StandardImportBehaviour',
    'GenerateDiffBehaviour',
    'ApplyDiffBehaviour',
]


class BaseImportBehaviour(object):
    """
    Base class for import behaviours.
    """
    save_changes = True

    def __init__(self, key, model, serializer_cls):
        self.key = key
        self.model = model
        self.serializer_cls = serializer_cls

    def get_result_object(self, data):
        return ImportResult(self.key, self.model)

    @classmethod
    def transform_multi_input(cls, import_export_managers, input_data):
        pass

    def transform_input(self, input_data):
        pass

    def process_new_object(self, result, row, serializer):
        pass

    def process_updated_object(self, result, row, serializer):
        pass

    def process_unchanged_object(self, result, row, serializer):
        pass


class StandardImportBehaviour(BaseImportBehaviour, FieldHelper):
    """
    Imports and saves changes from Dataset objects.
    """
    save_changes = True

    @classmethod
    def transform_multi_input(cls, import_export_managers, input_data):
        for importer in import_export_managers:
            for file_data in input_data.get(importer.model, []):
                filename, data = file_data
                yield importer, filename, data

    def transform_input(self, input_data):
        serializer = self.serializer_cls()
        for row_data in input_data.dict:
            data = normalize_row_data(row_data)

            result = data.copy()
            for field_name, value in data.items():
                field = serializer.fields.get(field_name, None)
                if field:
                    val = self.from_string_representation(field, value)
                    result[field_name] = val
            yield result

    def process_new_object(self, result, row, serializer):
        return serializer.save()

    def process_updated_object(self, result, row, serializer):
        serializer.save()

    def process_unchanged_object(self, result, row, serializer):
        pass


class GenerateDiffBehaviour(StandardImportBehaviour):
    """
    Generates a "diff" based from Dataset objects.
    Inherits from StandardImportBehaviour,
    but generates a "diff" object instead of saving changes.
    """
    save_changes = False

    def get_result_object(self, data):
        result = super(GenerateDiffBehaviour, self).get_result_object(data)
        result.result['column_names'] = data.headers
        return result

    def process_new_object(self, result, row, serializer):
        res = {
            'type': 'new',
            'diff': serializer.get_diff_data(),
            'initial_data': serializer.initial_data
        }
        result.add_result(res,
                          row.line_number,
                          row.row_number)

        return serializer.create_temporary_instance()

    def process_updated_object(self, result, row, serializer):
        res = {
            'type': 'update',
            'diff': serializer.get_diff_data(),
            'initial_data': serializer.initial_data
        }
        result.add_result(res,
                          row.line_number,
                          row.row_number)

    def process_unchanged_object(self, result, row, serializer):
        res = {
            'type': 'unchanged',
            'diff': None,
            'initial_data': serializer.initial_data
        }
        result.add_result(res,
                          row.line_number,
                          row.row_number)


class ApplyDiffBehaviour(StandardImportBehaviour):
    """
    Applies a "diff" object.
    Inherits from StandardImportBehaviour, but reads a "diff" object.
    """

    @classmethod
    def transform_multi_input(cls, import_export_managers, input_data):
        files = input_data.get('files', [])
        for importer in import_export_managers:
            datasets = (f for f in files if f['model'] == importer.key)
            for dataset in datasets:
                yield importer, dataset.get('filename', ''), dataset

    def transform_input(self, input_data):
        for row_data in input_data.get('results', []):
            yield row_data.get('initial_data', {})
