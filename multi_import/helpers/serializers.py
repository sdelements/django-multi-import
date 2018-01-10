from collections import namedtuple

from rest_framework import relations
import six
from tablib.compat import unicode

from multi_import.helpers import fields, strings


FieldChange = namedtuple('FieldChange', ['field', 'old', 'new', 'value'])


def get_related_fields(serializer):
    return [
        field for field in serializer.fields.values()
        if isinstance(field, relations.RelatedField)
    ]


def get_many_related_fields(serializer):
    return [
        field for field in serializer.fields.values()
        if isinstance(field, relations.ManyRelatedField)
    ]


def get_dependencies(serializer):
    """
    Returns a list of related models that a serializer is dependent on.
    """
    result = []

    field_querysets = [
        (field, field.queryset)
        for field in get_related_fields(serializer)
    ]

    field_querysets.extend([
        (field, field.child_relation.queryset)
        for field in get_many_related_fields(serializer)
    ])

    for field, queryset in field_querysets:
        if field.read_only:
            continue

        if hasattr(queryset, 'model'):
            model = queryset.model
        else:
            model = queryset.related_model

        result.append(model)

    return result


def get_original_representation(serializer):
    if serializer.instance:
        return serializer.to_representation(serializer.instance)
    return {}


def get_changed_fields(serializer, validated_data=None):
    validated_data = validated_data or serializer.validated_data
    result = {}

    orig = get_original_representation(serializer)

    for field_name, field in serializer.fields.items():
        if field.read_only or field.write_only:
            continue

        source = unicode(field.source)

        if source not in validated_data:
            continue

        old_value = orig[field_name] if field_name in orig else None

        value = validated_data[source]
        new_value = field.to_representation(value)

        # TODO: Move this to .to_representation()?
        if isinstance(old_value, six.string_types):
            old_value = strings.normalize_string(old_value)

        if old_value != new_value:
            result[field_name] = FieldChange(field,
                                             old_value,
                                             new_value,
                                             value)

    return result


def has_changes(serializer, validated_data=None):
    return bool(get_changed_fields(serializer, validated_data))


def might_have_changes(serializer):
    submitted_fields = [
        (field_name, field)
        for field_name, field in serializer.fields.items()
        if field_name in serializer.initial_data
        and not field.read_only and not field.write_only
    ]

    orig_rep = get_original_representation(serializer)

    old_values = {
        field_name: (
            fields.to_string_representation(field, orig_rep[field_name])
            if field_name in orig_rep else ""
        )
        for field_name, field in submitted_fields
    }

    new_values = {
        field_name: fields.to_string_representation(
            field, serializer.initial_data[field_name]
        )
        for field_name, field in submitted_fields
    }

    return old_values != new_values


def get_diff_data(serializer):
    if not has_changes(serializer):
        return None

    data = {}

    changed_fields = get_changed_fields(serializer)
    orig = get_original_representation(serializer)

    for column_name in serializer.initial_data:
        field = serializer.fields.get(column_name, None)
        if not field:
            continue

        data[column_name] = field_data = []

        if column_name in orig:
            field_data.append(
                fields.to_string_representation(field, orig[column_name])
            )
        else:
            field_data.append(u'')

        field_change = changed_fields.get(column_name, None)

        if not field_change:
            continue

        new_value = field_change.new

        field_data.append(
            fields.to_string_representation(field, new_value)
        )

    return data
