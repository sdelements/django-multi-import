from django.core.exceptions import MultipleObjectsReturned

from multi_import.object_cache import CachedQuery


__all__ = [
    'Importer',
]


class Row(object):
    """
    Represents a row in an imported Dataset
    """
    def __init__(self, row_number, line_number, row_data):
        self.row_number = row_number
        self.line_number = line_number
        self.data = row_data


class Importer(object):
    lookup_fields = ('pk',)

    error_messages = {
        'cannot_update': u'Can not update this item.',
        'multiple_matches': u'Multiple database entries match.'
    }

    def __init__(self,
                 import_behaviour,
                 key,
                 model,
                 lookup_fields,
                 queryset,
                 serializer):

        self.import_behaviour = import_behaviour
        self.key = key
        self.model = model
        self.lookup_fields = lookup_fields
        self.queryset = queryset
        self.serializer = serializer
        self.cached_query = self.get_cached_query()

    def get_serializer_context(self, context=None):
        context = context or {}
        context['cached_query'] = self.cached_query
        return context

    def can_update_object(self, instance):
        return True

    def get_cached_query(self):
        return CachedQuery(self.queryset, self.lookup_fields)

    def lookup_model_object(self, row):
        return self.cached_query.lookup(self.lookup_fields, row.data)

    def enumerate_data(self, data):
        """
        Enumerates rows, and calculates row and line numbers
        """
        first_row_line_number = 2
        line_count = 0

        for row_number, row_data in enumerate(data, start=1):
            line_number = first_row_line_number + line_count
            line_count += 1 + sum([
                value.count('\n') for value in row_data.values()
            ])
            yield Row(row_number, line_number, row_data)

    def transform_input(self, input_data):
        pass

    def run(self, data, context=None):
        import_behaviour = self.import_behaviour(self.key,
                                                 self.model,
                                                 self.serializer)

        result = import_behaviour.get_result_object(data)

        input_data = import_behaviour.transform_input(data)

        for row in self.enumerate_data(input_data):
            try:
                instance = self.lookup_model_object(row)
            except MultipleObjectsReturned:
                result.add_row_error(row,
                                     self.error_messages['multiple_matches'])
                continue

            context = self.get_serializer_context(context)
            serializer = self.serializer(instance=instance,
                                         data=row.data,
                                         context=context,
                                         partial=True)

            if not serializer.might_have_changes:
                import_behaviour.process_unchanged_object(result,
                                                          row,
                                                          serializer)
                continue

            is_valid = serializer.is_valid()
            update_chk = instance and (serializer.has_changes or not is_valid)

            if update_chk and not self.can_update_object(instance):
                result.add_row_error(row, self.error_messages['cannot_update'])
                continue

            if not is_valid:
                for column_name, messages in serializer.errors.items():
                    result.add_row_errors(row, messages, column_name)
                continue

            if not serializer.has_changes:
                import_behaviour.process_unchanged_object(result,
                                                          row,
                                                          serializer)

            elif serializer.instance:
                import_behaviour.process_updated_object(result,
                                                        row,
                                                        serializer)

            else:
                import_behaviour.process_new_object(result, row, serializer)
                serializer.cache_new_object()

        return result