from django.core.exceptions import MultipleObjectsReturned, ValidationError
from six import string_types
from multi_import.object_cache import CachedQuery, ObjectCache
from multi_import.utils import normalize_string


class ImportResult(object):
    """
    Results from an attempt to generate an import diff.
    Contains a list of errors, or if successful, a diff object.
    """
    def __init__(self, model_key, model, mappings, lookup_fields):
        self.model = model
        self.errors = []
        self.diff = {
            'model': model_key,
            'attributes': [mapping.field_name for mapping in mappings],
            'column_names': [mapping.column_name for mapping in mappings],
            'updated_objects': [],
            'new_objects': [],
            'unchanged_objects': 0
        }
        self.new_object_refs = ObjectCache(lookup_fields)

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

    def add_new_object(self, attributes, line_number, row_number, instance):
        new_dict = {
            'line_number': line_number,
            'row_number': row_number,
            'attributes': [
                attributes.get(attribute, [''])
                for attribute in self.diff['column_names']
            ]
        }
        self.diff['new_objects'].append(new_dict)
        self.new_object_refs.cache_instance(instance)

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

    def __init__(self,
                 key,
                 model,
                 mappings,
                 field_mappings,
                 lookup_fields,
                 queryset,
                 object_resolver):

        self.key = key
        self.model = model
        self.mappings = mappings
        self.field_mappings = field_mappings
        self.lookup_fields = lookup_fields
        self.queryset = queryset
        self.object_resolver = object_resolver
        self.cached_query = self.get_cached_query()

    def can_update_object(self, instance):
        return True

    @property
    def writable_mappings(self):
        return [mapping for mapping in self.mappings if not mapping.readonly]

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
                value = str(value)

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

    def row_has_no_changes(self, file_mappings, row, instance):
        """
        Compares the imported values to a database instance,
        returns True if there are no changes.
        """
        if not instance:
            return False

        resolver = self.object_resolver
        columns = row.data.keys()
        resolved_values = resolver.resolve_export_values(instance,
                                                         columns)
        imported_dict = {
            mapping.field_name: row.data[mapping.column_name]
            for mapping in file_mappings
        }
        model_dict = {
            key: value.get_string()
            for key, value in resolved_values.dict.iteritems()
        }

        return dict(imported_dict) == dict(model_dict)

    def run_model_validation(self, resolved_values):
        """
        Instantiates a model using the resolved values,
        and runs full_clean() to validate.
        """
        model_errors = []

        model_data = {
            key: value.value
            for key, value in resolved_values.dict.iteritems()
            if value.mapping.model_init and not value.errors
        }

        exclude = [
            key for key, value in resolved_values.dict.iteritems()
            if value.exclude_from_model_validation
        ]

        try:
            instance = self.model(**model_data)
            instance.full_clean(exclude=exclude, validate_unique=False)

        except ValidationError as e:
            for field_name, errors in e.error_dict.iteritems():
                column_name = self.field_mappings[field_name].column_name
                model_errors.extend(
                    [(column_name, error.messages) for error in errors]
                )

        return instance, model_errors

    def get_diff_data(self,
                      row,
                      resolved_values,
                      file_mappings,
                      instance=None):

        if not instance:
            return dict(((k, [v]) for k, v in row.data.iteritems()))

        changes = {}

        column_names = [mapping.column_name for mapping in file_mappings]
        old_values = self.object_resolver.resolve_export_values(instance,
                                                                column_names)

        for old_value in old_values.list:
            mapping = old_value.mapping
            old_val_str = old_value.get_string()
            new_val = resolved_values.dict[mapping.field_name]
            new_val_str = new_val.get_string()

            if mapping.readonly or old_val_str == new_val_str:
                continue

            if (mapping.is_foreign_key and
                    not new_val.exclude_from_model_validation):
                changes[mapping.column_name] = [old_val_str,
                                                new_val_str,
                                                new_val.value.pk]
            else:
                changes[mapping.column_name] = [old_val_str,
                                                new_val_str]

        return changes if changes else None

    def add_to_diff_result(self,
                           result,
                           file_mappings,
                           row,
                           data,
                           instance):

        if instance.pk:
            changes = self.get_diff_data(row, data, file_mappings, instance)
            if changes:
                result.add_updated_object(changes,
                                          row.line_number,
                                          row.row_number,
                                          instance.pk)
            else:
                result.increment_unchanged_objects()

        else:
            changes = self.get_diff_data(row, data, file_mappings)
            result.add_new_object(changes,
                                  row.line_number,
                                  row.row_number,
                                  instance)

    def generate_import_diff(self, dataset, new_object_refs=None):
        if new_object_refs is None:
            new_object_refs = {}

        file_mappings = [
            mapping for mapping in self.mappings
            if mapping.column_name in dataset.headers
        ]

        result = ImportResult(self.key,
                              self.model,
                              file_mappings,
                              self.lookup_fields)

        for row in self.enumerate_dataset(dataset):

            try:
                instance = self.lookup_model_object(row)
            except MultipleObjectsReturned:
                result.add_row_error(row, 'Multiple database entries match.')
                continue

            if self.row_has_no_changes(file_mappings, row, instance):
                result.increment_unchanged_objects()
                continue

            if instance and not self.can_update_object(instance):
                result.add_row_error(row, 'Can not update this item.')
                continue

            resolver = self.object_resolver
            resolved_values = resolver.resolve_import_values(row.data,
                                                             new_object_refs)

            if resolved_values.errors:
                for mapping, errors in resolved_values.errors:
                    result.add_row_errors(row, errors, mapping.column_name)
                continue

            new_obj, model_errors = self.run_model_validation(resolved_values)
            if model_errors:
                for column_name, messages in model_errors:
                    result.add_row_errors(row, messages, column_name)
                continue

            self.add_to_diff_result(result,
                                    file_mappings,
                                    row,
                                    resolved_values,
                                    instance or new_obj)

        return result
