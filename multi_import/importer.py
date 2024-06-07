from itertools import chain

from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import Serializer
from tablib import Dataset

from multi_import.cache import CachedQuery, ObjectCache
from multi_import.data import ExportResult, ImportResult, Row, RowStatus
from multi_import.exceptions import InvalidFileError
from multi_import.formats import all_formats
from multi_import.helpers import fields, files, serializers, strings
from multi_import.helpers.exceptions import get_errors
from multi_import.helpers.transactions import transaction


class RowData(object):
    def __init__(self):
        self.diff = {}
        self.instance = None
        self.serializers = []

    def add_diff(self, diff):
        self.diff.update(**diff)


class Rows(object):
    def __init__(self, headers, rows=None):
        self.headers = headers
        self.rows = [(row, RowData()) for row in rows or []]

    def __iter__(self):
        for row in self.rows:
            yield row


class DataReader(object):
    def __init__(self, serializers):
        self.serializers = serializers

    def read(self, data):
        if isinstance(data, Dataset):
            return self.read_dataset(data)
        return Rows(headers=data.headers, rows=data.rows)

    def read_dataset(self, dataset):
        rows = self.read_dataset_rows(dataset)
        return Rows(headers=dataset.headers, rows=self.enumerate_data(rows))

    def enumerate_data(self, data):
        """
        Enumerates rows, and calculates row and line numbers
        """
        first_row_line_number = 2
        line_count = 0

        for row_number, row_data in enumerate(data, start=2):
            # Skip empty rows
            if not self.has_values(row_data):
                continue

            line_number = first_row_line_number + line_count
            line_count += 1 + sum([value.count("\n") for value in row_data.values()])

            yield Row(row_number, line_number, row_data)

    def has_values(self, row_data):
        return any(
            value
            for value in row_data.values()
            if value and (not isinstance(value, str) or not value.isspace())
        )

    def read_dataset_rows(self, dataset):
        serializers = self.serializers
        for row_data in dataset.dict:
            data = self.normalize_row_data(row_data)

            result = data.copy()
            for field_name, value in data.items():
                for serializer in serializers:
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
                value = ""

            if isinstance(value, float) and value.is_integer():
                value = int(value)

            if not isinstance(value, str):
                value = str(value)

            data[key] = strings.normalize_string(value)
        return data


class PostSaveValidator(Serializer):
    def __init__(self, row=None, serializers=None, *args, **kwargs):
        self.row = row
        self.serializers = serializers
        super().__init__(*args, **kwargs)

    def get_validators(self):
        validators = []
        for serializer in self.serializers:
            meta = getattr(serializer, "Meta", None)
            key = (
                "post_create_validators"
                if self.row.status == RowStatus.new
                else "post_update_validators"
            )
            validators.extend(getattr(meta, key, []))
        return validators

    def to_internal_value(self, data):
        return data

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class Importer(object):
    key = None
    model = None
    id_column = None
    lookup_fields = ("pk",)
    file_formats = all_formats
    export_filename = None

    cached_query = CachedQuery
    serializer = None  # Deprecated in favour of serializer_class
    serializer_class = None
    serializer_classes = None

    error_messages = {
        "cannot_update": _("Can not update this item."),
        "multiple_matches": _("Multiple database entries match."),
        "multiple_updates": _("This item is being updated more than once."),
    }

    def __init__(self):
        self.empty_serializers = [
            serializer() for serializer in self.get_serializer_classes()
        ]

    def get_serializer_classes(self):
        serializer = self.serializer_class or self.serializer
        return self.serializer_classes if self.serializer_classes else (serializer,)

    def get_export_filename(self):
        return self.export_filename or self.key

    @property
    def dependencies(self):
        """
        Returns a list of related models that this importer is dependent on.
        Only the dependencies of the first serializer are considered.
        """
        return serializers.get_dependencies(self.empty_serializers[0])

    def get_queryset(self):
        queryset = self.model.objects

        for serializer in self.empty_serializers:
            for field in serializers.get_related_fields(serializer):
                queryset = queryset.select_related(field.source)

            for field in serializers.get_many_related_fields(serializer):
                queryset = queryset.prefetch_related(field.source)

        return queryset

    def get_export_queryset(self):
        return self.get_queryset()

    def get_import_queryset(self):
        return self.get_queryset()

    def export(self, empty=False, context=None):
        serializer_context = self.get_export_serializer_context(context)
        serializers = [
            serializer_class(context=serializer_context)
            for serializer_class in self.get_serializer_classes()
        ]
        dataset = Dataset(headers=self.get_export_header(serializers))

        if not empty:
            for instance in self.get_export_queryset():
                dataset.append(self.get_export_row(serializers, instance))

        return ExportResult(
            dataset=dataset,
            empty=empty,
            example_row=self.get_example_row(serializers),
            file_formats=self.file_formats,
            filename=self.get_export_filename(),
            id_column=self.id_column,
        )

    def get_export_header(self, serializers):
        return [
            field_name
            for serializer in serializers
            for field_name, field in serializer.get_fields().items()
            if not field.write_only
        ]

    def get_example_row(self, serializers):
        return ["" for serializer in serializers for _ in serializer.fields]

    def get_export_row(self, serializers, instance):
        results = []
        for serializer in serializers:
            representation = serializer.to_representation(instance=instance)
            for column_name, value in representation.items():
                field = serializer.fields[column_name]
                string_value = fields.to_string_representation(field, value)
                results.append(strings.excel_escape(string_value))
        return results

    def get_serializer_context(self, context=None):
        return context.copy() if context else {}

    def get_export_serializer_context(self, context=None):
        return self.get_serializer_context(context)

    def get_import_serializer_context(self, context=None):
        context = self.get_serializer_context(context)

        if "model_contexts" not in context:
            context["model_contexts"] = {}

        if self.model not in context["model_contexts"]:
            context["model_contexts"][self.model] = self.get_model_context()

        context["cached_query"] = self.get_cached_query()

        return context

    def get_model_context(self):
        return {"new_objects": ObjectCache(self.lookup_fields), "loaded_pks": set()}

    def can_update_object(self, instance):
        return True

    def get_cached_query(self):
        return self.cached_query(self.get_import_queryset(), self.lookup_fields)

    @transaction
    def import_file(self, file, context=None):
        try:
            dataset = files.read(self.file_formats, file)
        except InvalidFileError as e:
            return ImportResult(key=self.key, error=str(e))

        return self.import_data(dataset, context=context, transaction=False)

    @transaction
    def import_data(self, data, context=None):
        serializer_context = self.get_import_serializer_context(context)

        rows = self.read_rows(data)

        self.load_instances(rows, serializer_context)

        steps = len(self.get_serializer_classes())

        for step in range(steps):
            self.process_rows(rows, serializer_context, step)

        self.validate_rows_post_save(rows)

        self.process_diffs(rows)

        return self.transform_rows_to_result(rows)

    def read_rows(self, data):
        data_reader = DataReader(self.empty_serializers)
        rows = data_reader.read(data)
        return rows

    def load_instances(self, rows, context):
        for row, data in rows:
            self.load_instance(row, data, context)

    def process_rows(self, rows, context, step_index):
        serializer_classes = self.get_serializer_classes()

        if step_index + 1 > len(serializer_classes):
            return

        serializer_class = serializer_classes[step_index]
        process_row = (
            self.process_row_first_pass
            if step_index == 0
            else self.process_row_subsequent_pass
        )

        rows_to_add = []
        rows_to_update = []

        for row, data in rows:
            if data.instance:
                rows_to_update.append((row, data))
            else:
                rows_to_add.append((row, data))

        # Process updates first, then create new objects
        for row, data in chain(rows_to_update, rows_to_add):
            process_row(row, data, context, serializer_class)

    def validate_rows_post_save(self, rows):
        for row, data in rows:
            self.validate_row_post_save(row, data)

    def process_diffs(self, rows):
        for row, data in rows:
            if row.status == RowStatus.new or row.status == RowStatus.update:
                row.diff = data.diff

    def transform_rows_to_result(self, rows):
        return ImportResult(
            key=self.key, headers=rows.headers, rows=[row for row, data in rows.rows]
        )

    def enumerate_data(self, data):
        """
        Enumerates rows, and calculates row and line numbers
        """
        first_row_line_number = 2
        line_count = 0

        for row_number, row_data in enumerate(data, start=2):
            line_number = first_row_line_number + line_count
            line_count += 1 + sum([value.count("\n") for value in row_data.values()])
            yield Row(row_number, line_number, row_data)

    def load_instance(self, row, data, context):
        cached_query = context["cached_query"]
        instance = None
        try:
            lookup_data = self.get_lookup_data(row)
            instance = self.lookup_model_object(cached_query, lookup_data)

        except MultipleObjectsReturned:
            row.set_error(self.error_messages["multiple_matches"])

        if not instance:
            return

        pk_set = context["model_contexts"][self.model]["loaded_pks"]
        if instance.pk in pk_set:
            row.set_error(self.error_messages["multiple_updates"])
        else:
            pk_set.add(instance.pk)
            data.instance = instance

    def get_lookup_data(self, row):
        serializers = self.empty_serializers
        data = {}
        for key, value in row.data.items():
            for serializer in serializers:
                field = serializer.fields.get(key, None)
                if field:
                    data[field.source] = value
        return data

    def lookup_model_object(self, cached_query, lookup_data):
        return cached_query.match(lookup_data, self.lookup_fields)

    def process_row_first_pass(self, row, data, context, serializer_class):
        serializer = serializer_class(
            instance=data.instance,
            data=row.data.copy(),
            context=context,
            partial=data.instance is not None,
        )

        does_not_have_changes = not serializers.might_have_changes(serializer)

        if does_not_have_changes:
            row.status = RowStatus.unchanged
            data.add_diff(serializers.get_diff_data(serializer, no_changes=True))
            return

        is_valid = serializer.is_valid()
        has_changes = serializers.has_changes(serializer)

        cannot_update = (
            data.instance
            and (has_changes or not is_valid)
            and not self.can_update_object(data.instance)
        )

        if cannot_update:
            row.set_error(self.error_messages["cannot_update"])
            return

        if not is_valid:
            row.set_errors(serializer.errors)
            return

        if not has_changes:
            row.status = RowStatus.unchanged
            data.add_diff(serializers.get_diff_data(serializer, no_changes=True))
            return

        try:
            creating = not data.instance
            data.add_diff(serializers.get_diff_data(serializer))
            data.instance = serializer.save()
            data.serializers.append(serializer)

            if creating:
                row.status = RowStatus.new
                self.cache_instance(context, data.instance)
            else:
                row.status = RowStatus.update

        except ValidationError as ex:
            errors = get_errors(ex)
            row.set_errors(errors)

    def process_row_subsequent_pass(self, row, data, context, serializer_class):
        if row.errors:
            return

        if not data.instance:
            return

        serializer = serializer_class(
            instance=data.instance,
            data=row.data.copy(),
            context=context,
            partial=data.instance is not None,
        )

        does_not_have_changes = not serializers.might_have_changes(serializer)

        if does_not_have_changes:
            data.add_diff(serializers.get_diff_data(serializer, no_changes=True))
            return

        is_valid = serializer.is_valid()

        if not is_valid:
            row.set_errors(serializer.errors)
            return

        if not serializers.has_changes(serializer):
            data.add_diff(serializers.get_diff_data(serializer, no_changes=True))
            return

        try:
            data.add_diff(serializers.get_diff_data(serializer))
            data.instance = serializer.save()
            data.serializers.append(serializer)

            if row.status == RowStatus.unchanged:
                row.status = RowStatus.update

        except ValidationError as ex:
            errors = get_errors(ex)
            row.set_errors(errors)

    def validate_row_post_save(self, row, data):
        if row.status not in (RowStatus.new, RowStatus.update):
            return

        validator = PostSaveValidator(
            data=data.instance, row=row, serializers=data.serializers
        )

        if not validator.is_valid():
            row.set_errors(validator.errors)

    def cache_instance(self, context, instance):
        new_object_cache = context["model_contexts"][self.model]["new_objects"]
        new_object_cache.add(instance)
