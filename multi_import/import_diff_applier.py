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

    def get_obj_changes_dict(self, attributes, obj, update=False):
        result = {}

        for attribute, values in zip(attributes, obj['attributes']):
            if update and len(values) == 1:
                # Skip this attribute - no change
                continue

            value = values[-1]  # Always take last value in values array

            if not value:
                continue

            mapping = next((mapping for mapping in self.mappings if mapping.field_name == attribute), None)

            if mapping:
                if mapping.is_foreign_key:
                    value = mapping.related_model.objects.get(pk=value)
                if mapping.is_one_to_many:
                    value = [
                        mapping.related_model.objects.get(pk=val)
                        for val in value.split(',')
                    ]

            result[attribute] = value

        return result

    def create_object(self, obj_data):
        instance = self.model(**obj_data)
        instance.full_clean()
        instance.save()

    def apply_diff(self, diff_data):
        new_objects = diff_data.get('new_objects', [])
        updated_objects = diff_data.get('updated_objects', [])
        diff_attributes = diff_data['attributes']

        for new_object in new_objects:
            obj_data = self.get_obj_changes_dict(diff_attributes, new_object)
            self.create_object(obj_data)

        for updated_object in updated_objects:
            obj = self.get_object_for_update(updated_object['id'])
            changes = self.get_obj_changes_dict(diff_attributes, updated_object, update=True)

            if changes:
                for attribute_name, new_value in changes.iteritems():
                    setattr(obj, attribute_name, new_value)

                obj.full_clean()
                obj.save()
