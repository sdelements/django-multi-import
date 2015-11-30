from multi_import.relations import RelatedField, ManyRelatedField


class ImportDiffApplier(object):
    """
    Applies a diff JSON object.
    """
    def __init__(self, model, queryset, serializer_factory):
        self.model = model
        self.queryset = queryset
        self.serializer = serializer_factory.default

    def get_object_for_update(self, obj_id):
        return self.queryset.get(pk=obj_id)

    def get_object_changes(self, columns, obj, update=False):
        changes = []
        for column_name, values in zip(columns, obj['attributes']):
            num_values = len(values)
            required_values = 3 if update else 2

            if num_values == 0 or update and num_values == 1:
                # Skip this attribute - no change
                continue

            value = values[-1]  # Always take last value in values array

            if not value:
                continue

            field = self.serializer.fields.get(column_name, None)

            if not field:
                continue

            if field.read_only:
                continue

            if isinstance(field, RelatedField):
                # TODO: Add support for new object refs
                if num_values != required_values:
                    continue
                if value:
                    value = field.related_model.objects.get(pk=value)

            if isinstance(field, ManyRelatedField):
                # TODO: Add support for new object refs
                if num_values != required_values:
                    continue
                expected_length = len(value)
                related_model = field.child_relation.related_model
                value = list(related_model.objects.filter(pk__in=value))
                if len(value) != expected_length:
                    raise field.child_relation.related_model.ObjectDoesNotExist

            changes.append((field, value))
        return changes

    def create_object(self, obj_data):
        instance = self.model(**obj_data)
        instance.full_clean()
        instance.save()
        return instance

    def set_one_to_many(self, instance, field, values):
        object_manager = getattr(instance, field.source)
        object_manager.clear()
        for value in values:
            object_manager.add(value)

    def process_new_objects(self, diff_columns, new_objects):
        for new_object in new_objects:
            changes = self.get_object_changes(diff_columns, new_object)

            data = {
                field.source: value
                for field, value in changes
                if field.model_init
            }

            instance = self.create_object(data)

            for field, value in changes:
                if isinstance(field, ManyRelatedField):
                    self.set_one_to_many(instance, field, value)

    def process_updated_objects(self, diff_columns, updated_objects):
        for updated_object in updated_objects:
            instance = self.get_object_for_update(updated_object['id'])

            changes = self.get_object_changes(diff_columns,
                                              updated_object,
                                              update=True)

            for field, value in changes:
                if isinstance(field, ManyRelatedField):
                    self.set_one_to_many(instance, field, value)
                else:
                    setattr(instance, field.source, value)

            instance.full_clean()
            instance.save()

    def apply_diff(self, diff_data):
        diff_columns = diff_data['column_names']
        new_objects = diff_data.get('new_objects', [])
        updated_objects = diff_data.get('updated_objects', [])

        self.process_new_objects(diff_columns, new_objects)
        self.process_updated_objects(diff_columns, updated_objects)
