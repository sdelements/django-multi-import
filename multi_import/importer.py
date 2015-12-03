from django.core.exceptions import MultipleObjectsReturned
from six import string_types
from tablib.compat import unicode

from multi_import.fields import FieldHelper
from multi_import.object_cache import CachedQuery
from multi_import.utils import normalize_string


__all__ = [
    'ImportResult',
    'Importer',
    'ImportBehaviour',
    'ImportDiffGenerator',
    'ImportDiffApplier',
]


class ImportResult(object):
    """
    Results from an attempt to generate an import diff.
    Contains a list of errors, or if successful, a diff object.
    """
    def __init__(self, model_key, model):
        self.model = model
        self.errors = []
        self.results = []
        self.result = {
            'model': model_key,
            'results': self.results
        }

    @property
    def valid(self):
        return len(self.errors) == 0

    def add_errors(self, errors):
        self.errors.extend(errors)

    def add_row_error(self, row, message, column_name=None):
        error = {
            'line_number': row.line_number,
            'row_number': row.row_number,
            'message': message
        }
        if column_name:
            error['attribute'] = column_name
        self.errors.append(error)

    def add_row_errors(self, row, messages, column_name=None):
        for message in messages:
            self.add_row_error(row, message, column_name)

    def add_result(self, result, line_number, row_number):
        result['line_number'] = line_number
        result['row_number'] = row_number
        self.results.append(result)


class Row(object):
    """
    Represents a row in an imported Dataset
    """
    def __init__(self, row_number, line_number, row_data):
        self.row_number = row_number
        self.line_number = line_number
        self.data = row_data


class Importer(object):
    lookup_fields = ('pk',)

    error_messages = {
        'cannot_update': u'Can not update this item.',
        'multiple_matches': u'Multiple database entries match.'
    }

    def __init__(self,
                 import_behaviour,
                 key,
                 model,
                 lookup_fields,
                 queryset,
                 serializer):

        self.import_behaviour = import_behaviour
        self.key = key
        self.model = model
        self.lookup_fields = lookup_fields
        self.queryset = queryset
        self.serializer = serializer
        self.cached_query = self.get_cached_query()

    def get_serializer_context(self, context=None):
        context = context or {}
        context['cached_query'] = self.cached_query
        return context

    def can_update_object(self, instance):
        return True

    def get_cached_query(self):
        return CachedQuery(self.queryset, self.lookup_fields)

    def lookup_model_object(self, row):
        return self.cached_query.lookup(self.lookup_fields, row.data)

    def get_result_object(self, input):
        return ImportResult(self.key, self.model)

    def enumerate_data(self, data):
        """
        Enumerates rows, and calculates row and line numbers
        """
        first_row_line_number = 2
        line_count = 0

        for row_number, row_data in enumerate(data, start=1):
            line_number = first_row_line_number + line_count
            line_count += 1 + sum([
                value.count('\n') for value in row_data.values()
            ])
            yield Row(row_number, line_number, row_data)

    def transform_input(self, input_data):
        pass

    def process_changes(self, result, row, serializer):
        pass

    def run(self, data, context=None):
        import_behaviour = self.import_behaviour(self.key,
                                                 self.model,
                                                 self.serializer)

        result = import_behaviour.get_result_object(data)

        input_data = import_behaviour.transform_input(data)

        for row in self.enumerate_data(input_data):
            try:
                instance = self.lookup_model_object(row)
            except MultipleObjectsReturned:
                result.add_row_error(row,
                                     self.error_messages['multiple_matches'])
                continue

            context = self.get_serializer_context(context)
            serializer = self.serializer(instance=instance,
                                         data=row.data,
                                         context=context,
                                         partial=True)

            is_valid = serializer.is_valid()
            update_chk = instance and (serializer.has_changes or not is_valid)

            if update_chk and not self.can_update_object(instance):
                result.add_row_error(row, self.error_messages['cannot_update'])
                continue

            if not is_valid:
                for column_name, messages in serializer.errors.items():
                    result.add_row_errors(row, messages, column_name)
                continue

            import_behaviour.process_changes(result, row, serializer)

        return result


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

    def process_changes(self, result, row, serializer):
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

    def process_changes(self, result, row, serializer):
        result.add_result(serializer.get_dryrun_results(),
                          row.line_number,
                          row.row_number)


class ImportDiffApplier(ImportBehaviour):
    """
    Applies a diff JSON object.
    """

    def transform_input(self, input_data):
        for row_data in input_data.get('results', []):
            yield row_data.get('initial_data', {})

    def process_changes(self, result, row, serializer):
        if serializer.has_changes:
            serializer.save()
