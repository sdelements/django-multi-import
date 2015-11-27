from django.db import models
from rest_framework.serializers import ModelSerializer as DrfModelSerializer
from rest_framework.utils import model_meta
import six
from tablib.compat import unicode

from multi_import import fields
from multi_import.relations import (LookupRelatedField,
                                    RelatedField,
                                    ManyRelatedField)
from multi_import.utils import normalize_string

__all__ = [
    'FieldInfo',
    'SerializerFactory',
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
            if isinstance(field, RelatedField)
        ]

    def many_related_fields(self):
        return [
            field for field in self.serializer.fields.values()
            if isinstance(field, ManyRelatedField)
        ]


class SerializerFactory(object):

    def __init__(self, serializer):
        self.serializer = serializer
        self.default = serializer()
        self.fields = FieldInfo(self.default)

    def get(self, *args, **kwargs):
        return self.serializer(*args, **kwargs)


class ModelSerializer(DrfModelSerializer):
    serializer_related_field = LookupRelatedField

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
    # if ModelDurationField is not None:
    #     serializer_field_mapping[ModelDurationField] = DurationField
    serializer_related_field = LookupRelatedField
    # serializer_url_field = HyperlinkedIdentityField
    # serializer_choice_field = ChoiceField

    @property
    def new_object_cache(self):
        return self.context['new_object_cache']

    @property
    def has_changes(self):
        if not hasattr(self, '_validated_data'):
            raise AssertionError(
                'You must call `.is_valid()` before accessing `.has_changes`.'
            )

        if not self.instance:
            return True

        orig = self.to_representation(self.instance)
        validated_data_keys = self.validated_data.keys()

        orig_subset = {}
        validated_data = {}

        for column_name, value in orig.items():
            field = self.fields[column_name]
            field_name = unicode(field.source)
            if field_name in validated_data_keys:

                # TODO: Move this to .to_representation()?
                if isinstance(value, six.string_types):
                    value = normalize_string(value)

                orig_subset[field_name] = value
                validated_data[field_name] = field.to_representation(
                    self.validated_data[field_name]
                )

        return orig_subset != validated_data

    def transform_input(self, data):
        result = data.copy()
        for field_name, value in data.iteritems():
            field = self.fields.get(field_name, None)
            if field:
                val = field.from_string_representation(value)
                result[field_name] = val
        return result

    def create_temporary_instance(self):
        if not hasattr(self, '_validated_data'):
            raise AssertionError(
                'You must call `.is_valid()` '
                'before calling `.create_temporary_instance()`.'
            )

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
