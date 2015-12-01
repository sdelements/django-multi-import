from collections import namedtuple

from django.db import models
from rest_framework.compat import DurationField as ModelDurationField
from rest_framework.serializers import ModelSerializer as DrfModelSerializer
from rest_framework.utils import model_meta
import six
from tablib.compat import unicode

from multi_import import fields
from multi_import import relations
from multi_import.utils import normalize_string

__all__ = [
    'FieldInfo',
    'SerializerFactory',
    'ImportExportSerializer',
    'ModelSerializer',
]


class FieldInfo(object):
    def __init__(self, serializer, column_names=None):
        self.serializer = serializer
        self.column_names = column_names or serializer.Meta.fields
        self.field_names = [
            self.serializer.fields[column_name].source
            for column_name in self.column_names
        ]

    def subset(self, column_names):
        return FieldInfo(self.serializer, column_names)

    @property
    def dependencies(self):
        """
        Returns a list of related models that this importer is dependent on.
        """
        result = []

        result.extend([
            field.related_model
            for field in self.related_fields()
            if not field.read_only
        ])

        result.extend([
            field.child_relation.related_model
            for field in self.many_related_fields()
            if not field.read_only
        ])

        return result

    def related_fields(self):
        return [
            field for field in self.serializer.fields.values()
            if isinstance(field, relations.RelatedFieldMixin)
        ]

    def many_related_fields(self):
        return [
            field for field in self.serializer.fields.values()
            if isinstance(field, relations.ManyRelatedField)
        ]


class SerializerFactory(object):

    def __init__(self, serializer):
        self.serializer = serializer
        self.default = serializer()
        self.fields = FieldInfo(self.default)

    def get(self, *args, **kwargs):
        return self.serializer(*args, **kwargs)


FieldChange = namedtuple('FieldChange', ['field', 'old', 'new', 'value'])


class ImportExportSerializer(object):

    @property
    def new_object_cache(self):
        return self.context['new_object_cache']

    @property
    def has_changes(self):
        return len(self.changed_fields) > 0

    @property
    def changed_fields(self):
        result = {}

        if self.instance:
            orig = self.to_representation(self.instance)
        else:
            orig = {}

        for field_name, field in self.fields.items():
            source = unicode(field.source)

            if source not in self.validated_data:
                continue

            old_value = orig[field_name] if field_name in orig else None

            # TODO: Move this to .to_representation()?
            if isinstance(old_value, six.string_types):
                old_value = normalize_string(old_value)

            value = self.validated_data[source]
            new_value = field.to_representation(value)

            if old_value != new_value:
                result[field_name] = FieldChange(field,
                                                 old_value,
                                                 new_value,
                                                 value)

        return result

    def transform_input(self, data):
        result = data.copy()
        for field_name, value in data.iteritems():
            field = self.fields.get(field_name, None)
            if field:
                val = field.from_string_representation(value)
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
        cache = self.new_object_cache[self.Meta.model]
        cache.cache_instance(instance)


class ModelSerializer(ImportExportSerializer, DrfModelSerializer):
    serializer_field_mapping = {
        models.AutoField: fields.IntegerField,
        models.BigIntegerField: fields.IntegerField,
        models.BooleanField: fields.BooleanField,
        models.CharField: fields.CharField,
        models.CommaSeparatedIntegerField: fields.CharField,
        models.DateField: fields.DateField,
        models.DateTimeField: fields.DateTimeField,
        models.DecimalField: fields.DecimalField,
        models.EmailField: fields.EmailField,
        models.Field: fields.ModelField,
        models.FileField: fields.FileField,
        models.FloatField: fields.FloatField,
        models.ImageField: fields.ImageField,
        models.IntegerField: fields.IntegerField,
        models.NullBooleanField: fields.NullBooleanField,
        models.PositiveIntegerField: fields.IntegerField,
        models.PositiveSmallIntegerField: fields.IntegerField,
        models.SlugField: fields.SlugField,
        models.SmallIntegerField: fields.IntegerField,
        models.TextField: fields.CharField,
        models.TimeField: fields.TimeField,
        models.URLField: fields.URLField,
        models.GenericIPAddressField: fields.IPAddressField,
        models.FilePathField: fields.FilePathField,
    }
    if ModelDurationField is not None:
        serializer_field_mapping[ModelDurationField] = fields.DurationField
    serializer_related_field = relations.LookupRelatedField
    serializer_url_field = relations.HyperlinkedIdentityField
    serializer_choice_field = fields.ChoiceField
