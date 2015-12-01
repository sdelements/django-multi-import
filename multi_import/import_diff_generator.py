from django.core.exceptions import MultipleObjectsReturned
from six import string_types
from tablib.compat import unicode

from multi_import.object_cache import CachedQuery
from multi_import.fields import empty
from multi_import.relations import ManyRelatedField, RelatedField
from multi_import.utils import normalize_string


class ImportResult(object):
    """
    Results from an attempt to generate an import diff.
    Contains a list of errors, or if successful, a diff object.
    """
    def __init__(self, model_key, model, column_names, field_names):
        self.model = model
        self.errors = []
        self.diff = {
            'model': model_key,
            'attributes': field_names,
            'column_names': column_names,
            'updated_objects': [],
            'new_objects': [],
            'unchanged_objects': 0
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

    def add_new_object(self, attributes, line_number, row_number):
        new_dict = {
            'line_number': line_number,
            'row_number': row_number,
            'attributes': [
                attributes.get(attribute, [''])
                for attribute in self.diff['column_names']
            ]
        }
        self.diff['new_objects'].append(new_dict)

    def add_updated_object(self, attributes, line_number, row_number, id):
        new_dict = {
            'line_number': line_number,
            'row_number': row_number,
            'attributes': [
                attributes.get(attribute, [''])
                for attribute in self.diff['column_names']
            ],
            'id': id
        }
        self.diff['updated_objects'].append(new_dict)

    def increment_unchanged_objects(self):
        self.diff['unchanged_objects'] += 1


class Row(object):
    """
    Represents a row in an imported Dataset
    """
    def __init__(self, row_number, line_number, row_data):
        self.row_number = row_number
        self.line_number = line_number
        self.data = row_data


class ImportDiffGenerator(object):
    """
    Generates a diff object based on an imported Dataset.
    """
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
                 serializer_factory):

        self.key = key
        self.model = model
        self.lookup_fields = lookup_fields
        self.queryset = queryset
        self.serializer_factory = serializer_factory
        self.cached_query = self.get_cached_query()

    def get_serializer_context(self, new_object_cache=None):
        return {
            'new_object_cache': new_object_cache
        }

    def can_update_object(self, instance):
        return True

    def get_cached_query(self):
        return CachedQuery(self.queryset, self.lookup_fields)

    def lookup_model_object(self, row):
        return self.cached_query.lookup(self.lookup_fields, row.data)

    def normalize_row_data(self, row_data):
        """
        Converts all values in row_data dict to strings.
        Required for Excel imports.
        """
        data = {}
        for key, value in row_data.iteritems():
            if value is None:
                value = ''

            if isinstance(value, float) and value.is_integer():
                value = int(value)

            if not isinstance(value, string_types):
                value = unicode(value)

            data[key] = normalize_string(value)
        return data

    def enumerate_dataset(self, dataset):
        """
        Enumerates rows, and calculates row and line numbers
        """
        first_row_line_number = 2
        line_count = 0

        for row_number, row_data in enumerate(dataset.dict, start=1):
            row_data = self.normalize_row_data(row_data)
            line_number = first_row_line_number + line_count
            line_count += 1 + sum([
                value.count('\n') for value in row_data.values()
            ])
            yield Row(row_number, line_number, row_data)

    def get_diff_data(self, dataset, row, serializer):
        if not serializer.has_changes:
            return None

        data = {}

        changed_fields = serializer.changed_fields

        if serializer.instance:
            orig = serializer.to_representation(serializer.instance)
        else:
            orig = {}

        for column_name in dataset.headers:
            field = serializer.fields.get(column_name, None)
            if not field:
                continue

            data[column_name] = field_data = []

            if column_name in orig:
                field_data.append(
                    field.to_string_representation(orig[column_name])
                )

            field_change = changed_fields.get(column_name, None)

            if not field_change:
                continue

            new_value = field_change.new

            field_data.append(
                field.to_string_representation(new_value)
            )

            value = field_change.value

            # TODO: Add handling for new object refs - they don't have a PK

            if isinstance(field, RelatedField):
                if not value or value is empty:
                    field_data.append(None)
                elif value.pk:
                    field_data.append(value.pk)

            if isinstance(field, ManyRelatedField):
                if value and value is not empty:
                    field_data.append(
                        [item.pk for item in value if item.pk]
                    )
                else:
                    field_data.append([])

        return data

    def add_to_diff_result(self, result, dataset, row, serializer):

        if serializer.instance:
            changes = self.get_diff_data(dataset, row, serializer)
            if changes:
                result.add_updated_object(changes,
                                          row.line_number,
                                          row.row_number,
                                          serializer.instance.pk)
            else:
                result.increment_unchanged_objects()

        else:
            changes = self.get_diff_data(dataset, row, serializer)
            result.add_new_object(changes,
                                  row.line_number,
                                  row.row_number)
            serializer.cache_new_object()

    def generate_import_diff(self, dataset, new_object_refs):

        file_fields = self.serializer_factory.fields.subset(dataset.headers)

        result = ImportResult(self.key,
                              self.model,
                              file_fields.column_names,
                              file_fields.field_names)

        for row in self.enumerate_dataset(dataset):
            try:
                instance = self.lookup_model_object(row)
            except MultipleObjectsReturned:
                result.add_row_error(row,
                                     self.error_messages['multiple_matches'])
                continue

            data = self.serializer_factory.default.transform_input(row.data)
            context = self.get_serializer_context(new_object_refs)
            serializer = self.serializer_factory.get(instance=instance,
                                                     data=data,
                                                     context=context)

            is_valid = serializer.is_valid()
            update_chk = instance and (serializer.has_changes or not is_valid)

            if update_chk and not self.can_update_object(instance):
                result.add_row_error(row, self.error_messages['cannot_update'])
                continue

            if not is_valid:
                for column_name, messages in serializer.errors.iteritems():
                    result.add_row_errors(row, messages, column_name)
                continue

            if not serializer.has_changes:
                result.increment_unchanged_objects()
                continue

            self.add_to_diff_result(result, dataset, row, serializer)

        return result
