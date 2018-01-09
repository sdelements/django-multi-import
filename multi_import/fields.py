from django.core.exceptions import (FieldError,
                                    MultipleObjectsReturned,
                                    ObjectDoesNotExist,
                                    ValidationError
                                    )
from django.utils.translation import ugettext_lazy as _
from rest_framework import relations


class LookupRelatedField(relations.RelatedField):
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

    def to_representation(self, value):
        for attribute in self.lookup_fields:
            try:
                return getattr(value, attribute)
            except AttributeError:
                continue
        return None

    @property
    def related_model(self):
        return self.queryset.model

    @property
    def new_object_cache(self):
        return (
            self.context.get('model_contexts', {})
                        .get(self.related_model, {})
                        .get('new_objects')
        )

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
            match = new_object_cache.find(value, self.lookup_fields)
            if match:
                return match

        return None

    def search_database(self, queryset, value):
        for attribute in self.lookup_fields:
            try:
                return queryset.get(**{attribute: value})
            except (FieldError, ObjectDoesNotExist, TypeError,
                    ValidationError, ValueError):
                continue
        raise ObjectDoesNotExist
