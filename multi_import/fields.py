from rest_framework import fields  # noqa

from multi_import.utils import normalize_string

__all__ = [
    'empty',
    'FieldMixin',
    'BooleanField',
    'CharField',
    'DateField',
    'DateTimeField',
    'DecimalField',
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
    def from_string_representation(self, value):
        if value:
            val = value.lower()
            if val == 'true' or val == 'yes' or val == '1':
                return True
            if val == 'false' or val == 'no' or val == '0':
                return False
        return empty


class CharField(fields.CharField, FieldMixin):
    pass


class DateField(fields.DateField, FieldMixin):
    pass


class DateTimeField(fields.DateTimeField, FieldMixin):
    pass


class DecimalField(fields.DecimalField, FieldMixin):
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
    def from_string_representation(self, value):
        if value:
            val = value.lower()
            if val == 'true' or val == 'yes' or val == '1':
                return True
            if val == 'false' or val == 'no' or val == '0':
                return False
        return None


class SlugField(fields.SlugField, FieldMixin):
    pass


class TimeField(fields.TimeField, FieldMixin):
    pass


class URLField(fields.URLField, FieldMixin):
    pass
