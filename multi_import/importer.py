from django.core.exceptions import MultipleObjectsReturned
from rest_framework.settings import api_settings
from six import string_types
from tablib import Dataset

from multi_import.fields import FieldHelper
from multi_import.object_cache import CachedQuery
from multi_import.utils import normalize_string


__all__ = [
    'Importer',
]


class Rows(object):
    def __init__(self, headers, rows=None):
        self.headers = headers
        self.rows = [
            (row, RowData())
            for row in rows or []
        ]

    def __iter__(self):
        for row in self.rows:
            yield row

    def processed(self):
        return all(data.processed for row, data in self.rows)


class RowStatus(object):
    unchanged = 1
    update = 2
    new = 3


class RowData(object):
    def __init__(self):
        self.instance = None
        self.processed = False


class Row(object):
    """
    Represents a row in an imported Dataset
    """
    def __init__(self, row_number, line_number, data):
        self.row_number = row_number
        self.line_number = line_number
        self.data = data
        self.errors = None
        self.status = None
        self.diff = None

    def set_error(self, message):
        self.errors = {
            api_settings.NON_FIELD_ERRORS_KEY: [message]
        }

    def set_errors(self, errors):
        self.errors = errors

    def to_json(self):
        return {
            'row_number': self.row_number,
            'line_number': self.line_number,
            'data': self.data,
            'errors': self.errors,
            'status': self.status,
            'diff': self.diff,
        }

    @classmethod
    def from_json(cls, data):
        row = cls(
            row_number=data['row_number'],
            line_number=data['line_number'],
            data=data['data']
        )
        row.errors = data['errors']
        row.status = data['status']
        row.diff = data['diff']
        return row


class Result(object):
    def __init__(self, key, headers, rows=None):
        self.key = key
        self.headers = headers
        self.rows = rows or []

    @property
    def valid(self):
        return not any(row.errors for row in self.rows)

    @property
    def errors(self):
        result = []
        for row in (row for row in self.rows if row.errors):
            for key, messages in row.errors.items():
                for message in messages:
                    error = {
                        'line_number': row.line_number,
                        'row_number': row.row_number,
                        'message': message
                    }
                    if key != api_settings.NON_FIELD_ERRORS_KEY:
                        error['attribute'] = key
                    result.append(error)
        return result

    @property
    def new_rows(self):
        return [row for row in self.rows if row.status == RowStatus.new]

    @property
    def updated_rows(self):
        return [row for row in self.rows if row.status == RowStatus.update]

    @property
    def unchanged_rows(self):
        return [row for row in self.rows if row.status == RowStatus.unchanged]

    @property
    def changes(self):
        return [row for row in self.rows if row.status != RowStatus.unchanged]

    def to_json(self):
        return {
            'key': self.key,
            'headers': self.headers,
            'rows': [row.to_json() for row in self.rows],
        }

    @classmethod
    def from_json(cls, data):
        return cls(
            key=data['key'],
            headers=data['headers'],
            rows=[Row.from_json(row) for row in data['rows']]
        )


class DataReader(FieldHelper):
    def __init__(self, serializer):
        self.serializer = serializer

    def read(self, data):
        if isinstance(data, Dataset):
            return self.read_dataset(data)
        return Rows(
            headers=data.headers,
            rows=data.rows
        )

    def read_dataset(self, dataset):
        rows = self.read_dataset_rows(dataset)
        return Rows(
            headers=dataset.headers,
            rows=self.enumerate_data(rows)
        )

    def enumerate_data(self, data):
        """
        Enumerates rows, and calculates row and line numbers
        """
        first_row_line_number = 2
        line_count = 0

        for row_number, row_data in enumerate(data, start=2):
            line_number = first_row_line_number + line_count
            line_count += 1 + sum([
                value.count('\n') for value in row_data.values()
            ])
            yield Row(row_number, line_number, row_data)

    def read_dataset_rows(self, dataset):
        serializer = self.serializer()
        for row_data in dataset.dict:
            data = self.normalize_row_data(row_data)

            result = data.copy()
            for field_name, value in data.items():
                field = serializer.fields.get(field_name, None)
                if field:
                    val = self.from_string_representation(field, value)
                    result[field_name] = val
            yield result

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


class Importer(object):
    lookup_fields = ('pk',)

    error_messages = {
        'cannot_update': u'Can not update this item.',
        'multiple_matches': u'Multiple database entries match.'
    }

    def __init__(self,
                 key,
                 model,
                 lookup_fields,
                 queryset,
                 serializer):

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

    def run(self, data, context=None):
        context = self.get_serializer_context(context)

        data_reader = DataReader(self.serializer)
        rows = data_reader.read(data)

        for row, data in rows:
            self.load_instance(row, data)

        for row, data in rows:
            self.process_row(row, data, context)

        return Result(
            key=self.key,
            headers=rows.headers,
            rows=[row for row, data in rows.rows]
        )

    def enumerate_data(self, data):
        """
        Enumerates rows, and calculates row and line numbers
        """
        first_row_line_number = 2
        line_count = 0

        for row_number, row_data in enumerate(data, start=2):
            line_number = first_row_line_number + line_count
            line_count += 1 + sum([
                value.count('\n') for value in row_data.values()
            ])
            yield Row(row_number, line_number, row_data)

    def load_instance(self, row, data):
        try:
            lookup_data = self.get_lookup_data(row)
            data.instance = self.lookup_model_object(lookup_data)
        except MultipleObjectsReturned:
            row.set_error(self.error_messages['multiple_matches'])
            data.processed = True

    def get_lookup_data(self, row):
        serializer = self.serializer()
        fields = serializer.fields
        data = {}
        for key, value in row.data.items():
            field = fields.get(key, None)
            if field:
                data[field.source] = value
        return data

    def lookup_model_object(self, lookup_data):
        return self.cached_query.match(lookup_data, self.lookup_fields)

    def process_row(self, row, data, context):
        if data.processed:
            return

        serializer = self.serializer(instance=data.instance,
                                     data=row.data,
                                     context=context,
                                     partial=data.instance is not None)

        if not serializer.might_have_changes:
            row.status = RowStatus.unchanged
            data.processed = True
            return

        is_valid = serializer.is_valid()

        cannot_update = (
            data.instance
            and (serializer.has_changes or not is_valid)
            and not self.can_update_object(data.instance)
        )

        if cannot_update:
            row.set_error(self.error_messages['cannot_update'])
            data.processed = True
            return

        if not is_valid:
            row.set_errors(serializer.errors)
            data.processed = True
            return

        if not serializer.has_changes:
            row.status = RowStatus.unchanged
            data.processed = True
            return

        if serializer.instance:
            row.status = RowStatus.update
            row.diff = serializer.get_diff_data()
            serializer.save()
            data.processed = True

        else:
            row.status = RowStatus.new
            row.diff = serializer.get_diff_data()
            data.instance = serializer.save()
            data.processed = True
            self.cache_instance(context, data.instance)

    def cache_instance(self, context, instance):
        new_object_cache = context.get('new_object_cache', None)
        if new_object_cache is not None:
            cache = new_object_cache[self.model]
            cache.add(instance)
