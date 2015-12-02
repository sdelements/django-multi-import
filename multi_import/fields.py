from rest_framework import relations

from multi_import.utils import normalize_string

__all__ = [
    'FieldHelper',
]


class FieldHelper(object):
    list_separator = ';'

    def to_string_representation(self, field, value):
        if hasattr(field, 'to_string_representation'):
            return field.to_string_representation(value)

        if isinstance(field, relations.ManyRelatedField):
            return self.many_to_string_representation(field, value)

        if value is None:
            value = ''

        return normalize_string(unicode(value))

    def from_string_representation(self, field, value):
        if hasattr(field, 'from_string_representation'):
            return field.to_string_representation(value)

        if isinstance(field, relations.ManyRelatedField):
            return self.many_from_string_representation(field, value)

        return value

    def many_to_string_representation(self, field, value):
        if value is None:
            value = []

        return unicode(self.list_separator).join([
            self.to_string_representation(field.child_relation, val)
            for val in value
        ])

    def many_from_string_representation(self, field, value):
        if not value:
            return []

        return [
            self.from_string_representation(field.child_relation, val)
            for val in value.split(self.list_separator)
        ]
