from django.db.models import FieldDoesNotExist
from django.db.models.fields.related import ReverseManyRelatedObjectsDescriptor


class Mapping(object):
    """
    User-defined column to model field mapping.
    """

    def __init__(self, column_name, field_name=None, readonly=False, lookup_fields=None):
        self.column_name = column_name
        self.field_name = field_name or column_name
        self.readonly = readonly
        self.lookup_fields = lookup_fields or ()


class BoundMapping(Mapping):
    """
    A Mapping object that has been bound to a model class.
    This is used for mapping objects used at runtime by the importer and exporters.
    """

    def __init__(self, mapping, model):
        super(BoundMapping, self).__init__(mapping.column_name,
                                           mapping.field_name,
                                           mapping.readonly,
                                           mapping.lookup_fields)

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

        if not self.lookup_fields:
            self.lookup_fields = ('universal_id', 'pk', 'title', 'name', 'text')

        if isinstance(self.related_object_descriptor, ReverseManyRelatedObjectsDescriptor):
            self.model_init = False
            self.is_one_to_many = True
        else:
            self.is_foreign_key = True

    @classmethod
    def bind_mapping(cls, mapping, model):
        return cls(mapping, model)

    @classmethod
    def bind_mappings(cls, mappings, model):
        return [cls.bind_mappings(mapping, model) for mapping in mappings]
