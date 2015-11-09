from django.core.exceptions import (FieldError,
                                    MultipleObjectsReturned,
                                    ObjectDoesNotExist)
from django.db.models import BooleanField

from multi_import.utils import normalize_string


class ResolvedValue(object):
    """
    A value that has been resolved by a ValueResolver.
    If errors occurred when attempting to resolve a value,
    the errors list will be populated.
    """
    def __init__(self, mapping, value, errors=None, exclude=False):
        self.mapping = mapping
        self.errors = errors or []
        self.value = value
        self.exclude_from_model_validation = exclude

    def _get_related_value(self, obj):
        for attribute in self.mapping.lookup_fields:
            try:
                return getattr(obj, attribute)
            except AttributeError:
                continue

        return None

    def get_string(self):
        if self.mapping.is_foreign_key:
            value = self._get_related_value(self.value)

        elif self.mapping.is_one_to_many:
            values = [
                str(self._get_related_value(item)) for item in self.value
            ]
            value = ",".join(values)

        elif self.value is None:
            value = ""

        else:
            value = self.value

        return normalize_string(unicode(value))


class ValueResolver(object):
    """
    An object that resolves import/values based on a BoundMapping.
    """
    error_messages = {
        'no_match': 'No match found for: {0}',
        'multiple_matches': 'Multiple matches found for: {0}'
    }

    def __init__(self, mapping):
        self.mapping = mapping

    def get_error_message(self, key, value):
        return self.error_messages[key].format(value)

    def resolve_export_value(self, instance):
        # Takes the model value and converts it to be displayed in an export.
        result = getattr(instance, self.mapping.field_name)

        if self.mapping.is_one_to_many:
            value = [item for item in result.all()]
        else:
            value = result

        return ResolvedValue(self.mapping, value)

    def resolve_import_value(self, source=None, new_object_refs=None):
        # Takes the imported value and converts it a model value.
        if source is None:
            source = {}
        if new_object_refs is None:
            new_object_refs = {}

        field_value = source.get(self.mapping.column_name, '')

        if self.mapping.is_foreign_key:
            return self.get_foreign_key_value(field_value, new_object_refs)
        elif self.mapping.is_one_to_many:
            return self.get_one_to_many_value(field_value, new_object_refs)
        elif isinstance(self.mapping.field, BooleanField):
            return self.get_boolean_value(field_value)
        else:
            return ResolvedValue(self.mapping, field_value)

    def get_boolean_value(self, field_value):
        if field_value:
            value = field_value.lower()
            if value == 'true' or value == 'yes':
                return ResolvedValue(self.mapping, True)
            if value == 'false' or value == 'no':
                return ResolvedValue(self.mapping, False)
        return ResolvedValue(self.mapping, None)

    def get_foreign_key_queryset(self):
        return self.mapping.related_object_descriptor.get_queryset()

    def get_foreign_key_value(self, field_value, new_object_refs):
        if not field_value:
            return ResolvedValue(self.mapping, None)

        queryset = self.get_foreign_key_queryset()
        error, value, exclude = self.lookup_related(queryset,
                                                    field_value,
                                                    new_object_refs)
        errors = [error] if error else []
        return ResolvedValue(self.mapping, value, errors, exclude)

    def get_one_to_many_queryset(self):
        return self.mapping.related_model.objects

    def get_one_to_many_value(self, field_value, new_object_refs):
        if not field_value:
            return ResolvedValue(self.mapping, [])

        errors = []
        values = []
        queryset = self.get_one_to_many_queryset()

        for val in field_value.split(','):
            error, value, exclude = self.lookup_related(queryset,
                                                        val.strip(),
                                                        new_object_refs)
            if error:
                errors.append(error)
            if value:
                values.append(value)

        return ResolvedValue(self.mapping, values, errors, exclude)

    def lookup_related(self, queryset, value, new_object_refs):
        new_object = self.search_new_objects(value, new_object_refs)
        if new_object:
            return new_object

        return self.search_database(queryset, value)

    def get_lookup_error(self, key, value):
        return self.error_messages[key].format(value), None, False

    def search_new_objects(self, value, new_object_refs):
        new_objs = new_object_refs.get(self.mapping.related_model, [])

        if new_objs:
            try:
                match = new_objs.lookup_value(value)
                if match:
                    return None, match, True
            except MultipleObjectsReturned:
                return self.get_lookup_error('multiple_matches', value)

        return None

    def search_database(self, queryset, value):
        for attribute in self.mapping.lookup_fields:
            try:
                return None, queryset.get(**{attribute: value}), False
            except (FieldError, ObjectDoesNotExist, ValueError):
                continue
            except MultipleObjectsReturned:
                return self.get_lookup_error('multiple_matches', value)

        return self.get_lookup_error('no_match', value)
