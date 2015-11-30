from rest_framework import fields  # noqa

from multi_import.utils import normalize_string

__all__ = [
    'empty',
    'FieldMixin',
    'BooleanField',
    'CharField',
    'ChoiceField',
    'DateField',
    'DateTimeField',
    'DecimalField',
    'DurationField',
    'EmailField',
    'FileField',
    'FilePathField',
    'FloatField',
    'ImageField',
    'IntegerField',
    'IPAddressField',
    'ModelField',
    'NullBooleanField',
    'SlugField',
    'TimeField',
    'URLField',
]


empty = fields.empty


class FieldMixin(object):

    def to_string_representation(self, value):
        if value is None:
            value = ''
        return normalize_string(unicode(value))

    def from_string_representation(self, value):
        return value


class BooleanField(fields.BooleanField, FieldMixin):
    pass


class CharField(fields.CharField, FieldMixin):
    pass


class ChoiceField(fields.ChoiceField, FieldMixin):
    pass


class DateField(fields.DateField, FieldMixin):
    pass


class DateTimeField(fields.DateTimeField, FieldMixin):
    pass


class DecimalField(fields.DecimalField, FieldMixin):
    pass


class DurationField(fields.DurationField, FieldMixin):
    pass


class EmailField(fields.EmailField, FieldMixin):
    pass


class FileField(fields.FileField, FieldMixin):
    pass


class FilePathField(fields.FilePathField, FieldMixin):
    pass


class FloatField(fields.FloatField, FieldMixin):
    pass


class ImageField(fields.ImageField, FieldMixin):
    pass


class IntegerField(fields.IntegerField, FieldMixin):
    pass


class IPAddressField(fields.IPAddressField, FieldMixin):
    pass


class ModelField(fields.ModelField, FieldMixin):
    pass


class NullBooleanField(fields.NullBooleanField, FieldMixin):
    pass


class SlugField(fields.SlugField, FieldMixin):
    pass


class TimeField(fields.TimeField, FieldMixin):
    pass


class URLField(fields.URLField, FieldMixin):
    pass
