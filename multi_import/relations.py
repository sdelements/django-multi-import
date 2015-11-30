from django.core.exceptions import (ObjectDoesNotExist,
                                    MultipleObjectsReturned,
                                    FieldError)
from django.utils.translation import ugettext_lazy as _
from rest_framework import relations
from tablib.compat import unicode

from multi_import.fields import FieldMixin


__all__ = [
    'MANY_RELATION_KWARGS',
    'ManyRelatedField',
    'RelatedFieldMixin',
    'RelatedField',
    'HyperlinkedRelatedField',
    'HyperlinkedIdentityField',
    'PrimaryKeyRelatedField',
    'SlugRelatedField',
    'StringRelatedField',
    'LookupRelatedField',
]


MANY_RELATION_KWARGS = tuple(
    list(relations.MANY_RELATION_KWARGS) + ['list_separator']
)


class ManyRelatedField(relations.ManyRelatedField, FieldMixin):
    def __init__(self, list_separator=u';', *args, **kwargs):
        self.list_separator = list_separator
        super(ManyRelatedField, self).__init__(*args, **kwargs)

    def to_string_representation(self, value):
        return unicode(self.list_separator).join([
            self.child_relation.to_string_representation(val)
            for val in value
        ])

    def from_string_representation(self, value):
        if not value:
            return []

        return [
            self.child_relation.from_string_representation(val)
            for val in value.split(self.list_separator)
        ]


class RelatedFieldMixin(FieldMixin):
    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs.keys():
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return ManyRelatedField(**list_kwargs)

    @property
    def related_model(self):
        return self.queryset.model



class RelatedField(RelatedFieldMixin, relations.RelatedField):
    pass


class HyperlinkedRelatedField(RelatedFieldMixin,
                              relations.HyperlinkedRelatedField):
    pass


class HyperlinkedIdentityField(RelatedFieldMixin,
                               relations.HyperlinkedIdentityField):
    pass


class PrimaryKeyRelatedField(RelatedFieldMixin,
                             relations.PrimaryKeyRelatedField):
    pass


class SlugRelatedField(RelatedFieldMixin, relations.SlugRelatedField):
    pass


class StringRelatedField(RelatedFieldMixin, relations.StringRelatedField):
    pass


class LookupRelatedField(RelatedField):
    default_error_messages = {
        'required': _(u'This field is required.'),
        'does_not_exist': _(u'No match found for: "{value}".'),
        'multiple_matches': _(u'Multiple matches found for: {value}'),
    }

    def __init__(self, **kwargs):
        self.lookup_fields = kwargs.pop('lookup_fields', ['pk'])
        super(LookupRelatedField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            return self.lookup_related(self.get_queryset(), data)
        except MultipleObjectsReturned:
            self.fail('multiple_matches', value=data)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', value=data)
        # except (TypeError, ValueError):
        #     self.fail('incorrect_type', data_type=type(data).__name__)

    def to_representation(self, value):
        for attribute in self.lookup_fields:
            try:
                return getattr(value, attribute)
            except AttributeError:
                continue
        return None

    @property
    def new_object_cache(self):
        return self.context['new_object_cache'].get(self.related_model, None)

    def lookup_related(self, queryset, value):
        if not value:
            return None

        new_object = self.search_new_objects(value)
        if new_object:
            return new_object

        return self.search_database(queryset, value)

    def search_new_objects(self, value):
        new_object_cache = self.new_object_cache
        if new_object_cache:
            match = new_object_cache.lookup_value(value)
            if match:
                return match

        return None

    def search_database(self, queryset, value):
        for attribute in self.lookup_fields:
            try:
                return queryset.get(**{attribute: value})
            except (FieldError, ObjectDoesNotExist, ValueError):
                continue
        raise ObjectDoesNotExist
