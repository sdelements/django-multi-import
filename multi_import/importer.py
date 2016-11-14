from django.core.exceptions import MultipleObjectsReturned
from django.utils.translation import ugettext_lazy as _
from six import string_types
from tablib import Dataset

from multi_import.cache import CachedQuery
from multi_import.data import ImportResult, RowStatus, Row
from multi_import.exceptions import InvalidFileError
from multi_import.formats import all_formats
from multi_import.helpers import fields, files, serializers, strings
from multi_import.helpers.transactions import transaction


class RowData(object):
    def __init__(self):
        self.instance = None
        self.processed = False


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


class DataReader(object):
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
                    val = fields.from_string_representation(field, value)
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

            data[key] = strings.normalize_string(value)
        return data


class Importer(object):
    key = None
    model = None
    id_column = None
    lookup_fields = ('pk',)
    file_formats = all_formats

    cached_query = CachedQuery
    serializer = None

    error_messages = {
        'cannot_update': _(u'Can not update this item.'),
        'multiple_matches': _(u'Multiple database entries match.')
    }

    @property
    def dependencies(self):
        """
        Returns a list of related models that this importer is dependent on.
        """
        return serializers.get_dependencies(self.serializer())

    def get_queryset(self):
        queryset = self.model.objects
        serializer = self.serializer()

        for field in serializers.get_related_fields(serializer):
            queryset = queryset.select_related(field.source)

        for field in serializers.get_many_related_fields(serializer):
            queryset = queryset.prefetch_related(field.source)

        return queryset

    def get_export_queryset(self):
        return self.get_queryset()

    def get_import_queryset(self):
        return self.get_queryset()

    def export_file(self, empty=False, file_format=None):
        dataset = self.export_dataset(empty=empty)
        return files.write(self.file_formats, dataset, file_format=file_format)

    def export_dataset(self, empty=False):
        serializer = self.serializer()
        dataset = Dataset(headers=self.get_export_header(serializer))

        if not empty:
            for instance in self.get_export_queryset():
                dataset.append(self.get_export_row(serializer, instance))

        return dataset

    def get_export_header(self, serializer):
        return [
            field_name
            for field_name, field in serializer.get_fields().items()
            if not field.write_only
        ]

    def get_export_row(self, serializer, instance):
        results = []
        representation = serializer.to_representation(instance=instance)
        for column_name, value in representation.items():
            field = serializer.fields[column_name]
            val = fields.to_string_representation(field, value)
            # TODO: Excel escaping should be done for Excel/CSV formats
            results.append(strings.excel_escape(val))
        return results

    def get_serializer_context(self, cached_query, context=None):
        context = context or {}
        context['cached_query'] = cached_query
        return context

    def can_update_object(self, instance):
        return True

    def get_cached_query(self):
        return self.cached_query(
            self.get_import_queryset(), self.lookup_fields
        )

    @transaction
    def import_file(self, file):
        try:
            dataset = files.read(self.file_formats, file)
        except InvalidFileError as e:
            return ImportResult(
                key=self.key,
                error=e.message
            )

        return self.import_data(dataset, transaction=False)

    @transaction
    def import_data(self, data, context=None):
        cached_query = self.get_cached_query()
        context = self.get_serializer_context(cached_query, context)

        data_reader = DataReader(self.serializer)
        rows = data_reader.read(data)

        for row, data in rows:
            self.load_instance(row, data, cached_query)

        for row, data in rows:
            self.process_row(row, data, context)

        return ImportResult(
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

    def load_instance(self, row, data, cached_query):
        try:
            lookup_data = self.get_lookup_data(row)
            data.instance = self.lookup_model_object(cached_query, lookup_data)
        except MultipleObjectsReturned:
            row.set_error(self.error_messages['multiple_matches'])
            data.processed = True

    def get_lookup_data(self, row):
        serializer = self.serializer()
        data = {}
        for key, value in row.data.items():
            field = serializer.fields.get(key, None)
            if field:
                data[field.source] = value
        return data

    def lookup_model_object(self, cached_query, lookup_data):
        return cached_query.match(lookup_data, self.lookup_fields)

    def process_row(self, row, data, context):
        if data.processed:
            return

        serializer = self.serializer(instance=data.instance,
                                     data=row.data,
                                     context=context,
                                     partial=data.instance is not None)

        if not serializers.might_have_changes(serializer):
            row.status = RowStatus.unchanged
            data.processed = True
            return

        is_valid = serializer.is_valid()
        has_changes = serializers.has_changes(serializer)

        cannot_update = (
            data.instance
            and (has_changes or not is_valid)
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

        if not has_changes:
            row.status = RowStatus.unchanged
            data.processed = True
            return

        if serializer.instance:
            row.status = RowStatus.update
            row.diff = serializers.get_diff_data(serializer)
            serializer.save()
            data.processed = True

        else:
            row.status = RowStatus.new
            row.diff = serializers.get_diff_data(serializer)
            data.instance = serializer.save()
            data.processed = True
            self.cache_instance(context, data.instance)

    def cache_instance(self, context, instance):
        new_object_cache = context.get('new_object_cache', None)
        if new_object_cache is not None:
            cache = new_object_cache[self.model]
            cache.add(instance)
