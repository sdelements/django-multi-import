from six import string_types
from tablib.compat import unicode

from multi_import.fields import FieldHelper
from multi_import.import_result import ImportResult
from multi_import.utils import normalize_string


__all__ = [
    'ImportBehaviour',
    'ImportDiffGenerator',
    'ImportDiffApplier',
]


class ImportBehaviour(object):
    """
    Generates a diff object based on an imported Dataset.
    """
    def __init__(self, key, model, serializer):
        self.key = key
        self.model = model
        self.serializer_cls = serializer

    def get_result_object(self, input_data):
        return ImportResult(self.key, self.model)

    def transform_input(self, input_data):
        pass

    def process_new_object(self, result, row, serializer):
        pass

    def process_updated_object(self, result, row, serializer):
        pass

    def process_unchanged_object(self, result, row, serializer):
        pass


class ImportDiffGenerator(ImportBehaviour, FieldHelper):
    """
    Generates a diff object based on an imported Dataset.
    """
    def __init__(self, *args, **kwargs):
        super(ImportDiffGenerator, self).__init__(*args, **kwargs)
        self.serializer = self.serializer_cls()

    def get_result_object(self, input_data):
        result = super(ImportDiffGenerator, self).get_result_object(input_data)
        result.result['column_names'] = input_data.headers
        return result

    def normalize_row_data(self, row_data):
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

    def transform_input(self, input_data):
        for row_data in input_data.dict:
            data = self.normalize_row_data(row_data)

            result = data.copy()
            for field_name, value in data.items():
                field = self.serializer.fields.get(field_name, None)
                if field:
                    val = self.from_string_representation(field, value)
                    result[field_name] = val
            yield result

    def process_new_object(self, result, row, serializer):
        res = {
            'type': 'new',
            'diff': serializer.get_diff_data(),
            'initial_data': serializer.initial_data
        }
        result.add_result(res,
                          row.line_number,
                          row.row_number)

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


class ImportDiffApplier(ImportBehaviour):
    """
    Applies a diff JSON object.
    """

    def transform_input(self, input_data):
        for row_data in input_data.get('results', []):
            yield row_data.get('initial_data', {})

    def process_new_object(self, result, row, serializer):
        serializer.save()

    def process_updated_object(self, result, row, serializer):
        serializer.save()

    def process_unchanged_object(self, result, row, serializer):
        pass
