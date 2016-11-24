from rest_framework import relations
from tablib.compat import unicode

from multi_import.helpers import strings


list_separator = ';'


def to_string_representation(field, value):
    if hasattr(field, 'to_string_representation'):
        return field.to_string_representation(value)

    if isinstance(field, relations.ManyRelatedField):
        if value is None:
            value = []

        return unicode(list_separator).join([
            to_string_representation(field.child_relation, val)
            for val in value
        ])

    if value is None:
        value = ''

    return strings.normalize_string(unicode(value))


def from_string_representation(field, value):
    if hasattr(field, 'from_string_representation'):
        return field.from_string_representation(value)

    if not isinstance(field, relations.ManyRelatedField):
        return value

    if not value:
        return []

    return [
        from_string_representation(field.child_relation, val)
        for val in value.split(list_separator)
        if val and not val.isspace()
    ]
