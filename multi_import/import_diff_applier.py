class ImportDiffApplier(object):
    """
    Applies a diff JSON object.
    """

    def __init__(self, model, mappings, queryset):
        self.model = model
        self.mappings = mappings
        self.queryset = queryset

    def get_object_for_update(self, obj_id):
        return self.queryset.get(pk=obj_id)

    def get_object_changes(self, attributes, obj, update=False):
        for attribute, values in zip(attributes, obj['attributes']):
            if update and len(values) == 1:
                # Skip this attribute - no change
                continue

            value = values[-1]  # Always take last value in values array

            if not value:
                continue

            mapping = next((
                mapping for mapping in self.mappings
                if mapping.field_name == attribute
            ), None)

            if mapping:
                if mapping.is_foreign_key:
                    value = mapping.related_model.objects.get(pk=value)
                if mapping.is_one_to_many:
                    value = [
                        mapping.related_model.objects.get(pk=val)
                        for val in value.split(',')
                    ]

            yield mapping, value

    def create_object(self, obj_data):
        instance = self.model(**obj_data)
        instance.full_clean()
        instance.save()
        return instance

    def process_new_objects(self, diff_attributes, new_objects):
        for new_object in new_objects:
            changes = self.get_object_changes(diff_attributes, new_object)

            data = {
                mapping.field_name: value
                for mapping, value in changes
                if mapping.model_init
            }

            instance = self.create_object(data)

            for mapping, value in changes:
                if mapping.is_one_to_many:
                    object_manager = getattr(instance, mapping.field_name)
                    object_manager.clear()
                    for val in value:
                        object_manager.add(val)

    def process_updated_objects(self, diff_attributes, updated_objects):
        for updated_object in updated_objects:
            obj = self.get_object_for_update(updated_object['id'])

            changes = self.get_object_changes(diff_attributes,
                                              updated_object,
                                              update=True)

            for mapping, value in changes:
                setattr(obj, mapping.field_name, value)

            obj.full_clean()
            obj.save()

    def apply_diff(self, diff_data):
        diff_attributes = diff_data['attributes']
        new_objects = diff_data.get('new_objects', [])
        updated_objects = diff_data.get('updated_objects', [])

        self.process_new_objects(diff_attributes, new_objects)
        self.process_updated_objects(diff_attributes, updated_objects)
