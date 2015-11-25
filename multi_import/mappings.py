from django.db.models import FieldDoesNotExist
from django.db.models.fields.related import ReverseManyRelatedObjectsDescriptor
from django.utils.functional import cached_property


class Mapping(object):
    """
    User-defined column to model field mapping.
    """

    def __init__(self,
                 column_name,
                 field_name=None,
                 readonly=False,
                 lookup_fields=None,
                 list_separator=';'):

        self.column_name = column_name
        self.field_name = field_name or column_name
        self.readonly = readonly
        self.lookup_fields = lookup_fields or ()
        self.list_separator = list_separator


class MappingCollection(tuple):

    @cached_property
    def columns(self):
        return {mapping.column_name: mapping for mapping in self}

    @cached_property
    def fields(self):
        return {mapping.field_name: mapping for mapping in self}

    @cached_property
    def column_names(self):
        return [mapping.column_name for mapping in self]

    @cached_property
    def writable(self):
        return MappingCollection([
            mapping for mapping in self if not mapping.readonly
        ])

    def filter_by_columns(self, column_names):
        return MappingCollection([
            mapping for mapping in self
            if mapping.column_name in column_names
        ])


class BoundMapping(Mapping):
    """
    A Mapping object that has been bound to a model class.
    """

    def __init__(self, mapping, model, default_lookup_fields=None):
        lookup_fields = (
            mapping.lookup_fields or default_lookup_fields or ('pk',)
        )

        super(BoundMapping, self).__init__(mapping.column_name,
                                           mapping.field_name,
                                           mapping.readonly,
                                           lookup_fields,
                                           mapping.list_separator)

        self.model = model
        self.field = None
        self.related_object_descriptor = None
        self.is_relationship = False
        self.related_model = None
        self.is_one_to_many = False
        self.is_foreign_key = False

        self.model_init = not self.readonly

        try:
            self.field = model._meta.get_field_by_name(self.field_name)[0]
        except FieldDoesNotExist:
            # Probably a property
            self.readonly = True
            self.model_init = False
            return

        self.related_object_descriptor = getattr(model, self.field_name, None)

        if not self.related_object_descriptor:
            return

        self.is_relationship = True

        if hasattr(self.field, 'related_model'):
            self.related_model = self.field.related_model
        else:
            self.related_model = self.field.related.parent_model

        if isinstance(self.related_object_descriptor,
                      ReverseManyRelatedObjectsDescriptor):
            self.model_init = False
            self.is_one_to_many = True
        else:
            self.is_foreign_key = True

    @classmethod
    def bind_mapping(cls, mapping, model, default_lookup_fields=None):
        return cls(mapping, model, default_lookup_fields)

    @classmethod
    def bind_mappings(cls, mappings, model, default_lookup_fields=None):
        return MappingCollection([
            cls.bind_mapping(mapping, model, default_lookup_fields)
            for mapping in mappings
        ])
