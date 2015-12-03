from collections import namedtuple

from rest_framework import relations
from rest_framework.serializers import Serializer
from rest_framework.utils import model_meta
import six
from tablib.compat import unicode

from multi_import import FieldHelper
from multi_import.utils import normalize_string


__all__ = [
    'ImportExportSerializer',
]


FieldChange = namedtuple('FieldChange', ['field', 'old', 'new', 'value'])


class ImportExportSerializer(FieldHelper, Serializer):

    @property
    def dependencies(self):
        """
        Returns a list of related models that this importer is dependent on.
        """
        result = []

        fields = [
            (field, field.queryset)
            for field in self.related_fields()
        ]

        fields.extend([
            (field, field.child_relation.queryset)
            for field in self.many_related_fields()
        ])

        for field, queryset in fields:
            if field.read_only:
                continue

            if hasattr(queryset, 'model'):
                model = queryset.model
            else:
                model = queryset.related_model

            result.append(model)

        return result

    def related_fields(self):
        return [
            field for field in self.fields.values()
            if isinstance(field, relations.RelatedField)
        ]

    def many_related_fields(self):
        return [
            field for field in self.fields.values()
            if isinstance(field, relations.ManyRelatedField)
        ]

    @property
    def has_changes(self):
        return bool(self.changed_fields)

    @property
    def changed_fields(self):
        result = {}

        orig = self.to_representation(self.instance) if self.instance else {}

        for field_name, field in self.fields.items():
            source = unicode(field.source)

            if source not in self.validated_data:
                continue

            old_value = orig[field_name] if field_name in orig else None

            value = self.validated_data[source]
            new_value = field.to_representation(value)

            # TODO: Move this to .to_representation()?
            if isinstance(old_value, six.string_types):
                old_value = normalize_string(old_value)

            if old_value != new_value:
                result[field_name] = FieldChange(field,
                                                 old_value,
                                                 new_value,
                                                 value)

        return result

    def transform_input(self, data):
        result = data.copy()
        for field_name, value in data.items():
            field = self.fields.get(field_name, None)
            if field:
                val = self.from_string_representation(field, value)
                result[field_name] = val
        return result

    def create_temporary_instance(self):
        validated_data = self.validated_data.copy()

        ModelClass = self.Meta.model

        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        return ModelClass(**validated_data)

    def cache_new_object(self):
        instance = self.create_temporary_instance()
        new_object_cache = self.context.get('new_object_cache', None)
        if new_object_cache is not None:
            cache = new_object_cache[self.Meta.model]
            cache.cache_instance(instance)

    def get_diff_data(self):
        if not self.has_changes:
            return None

        data = {}

        changed_fields = self.changed_fields

        orig = self.to_representation(self.instance) if self.instance else {}

        for column_name in self.initial_data:
            field = self.fields.get(column_name, None)
            if not field:
                continue

            data[column_name] = field_data = []

            if column_name in orig:
                field_data.append(
                    self.to_string_representation(field, orig[column_name])
                )
            else:
                field_data.append(u'')

            field_change = changed_fields.get(column_name, None)

            if not field_change:
                continue

            new_value = field_change.new

            field_data.append(
                self.to_string_representation(field, new_value)
            )

        return data

    def get_dryrun_results(self):
        diff = self.get_diff_data()
        change_type = 'new'
        if self.instance:
            change_type = 'update'
        if not diff:
            change_type = 'unchanged'

        self.cache_new_object()

        return {
            'type': change_type,
            'diff': self.get_diff_data(),
            'initial_data': self.initial_data
        }
