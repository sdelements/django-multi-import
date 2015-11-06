from django.test import TestCase

from multi_import.mappings import Mapping, BoundMapping
from test.models import Person


class MappingTests(TestCase):

    def test_simple_field(self):
        mapping = Mapping('first_name')
        bound_mapping = BoundMapping.bind_mapping(mapping, Person)

        self.assertEqual(bound_mapping.model, Person)
        self.assertEqual(bound_mapping.column_name, 'first_name')
        self.assertEqual(bound_mapping.field_name, 'first_name')
        self.assertEqual(bound_mapping.readonly, False)
        self.assertEqual(bound_mapping.model_init, True)

    def test_custom_column_name(self):
        mapping = Mapping('name', 'first_name')
        bound_mapping = BoundMapping.bind_mapping(mapping, Person)

        self.assertEqual(bound_mapping.model, Person)
        self.assertEqual(bound_mapping.column_name, 'name')
        self.assertEqual(bound_mapping.field_name, 'first_name')
        self.assertEqual(bound_mapping.readonly, False)
        self.assertEqual(bound_mapping.model_init, True)

    def test_readonly(self):
        mapping = Mapping('first_name', readonly=True)
        bound_mapping = BoundMapping.bind_mapping(mapping, Person)

        self.assertEqual(bound_mapping.model, Person)
        self.assertEqual(bound_mapping.column_name, 'first_name')
        self.assertEqual(bound_mapping.field_name, 'first_name')
        self.assertEqual(bound_mapping.readonly, True)
        self.assertEqual(bound_mapping.model_init, False)

    def test_property(self):
        mapping = Mapping('name')
        bound_mapping = BoundMapping.bind_mapping(mapping, Person)

        self.assertEqual(bound_mapping.model, Person)
        self.assertEqual(bound_mapping.column_name, 'name')
        self.assertEqual(bound_mapping.field_name, 'name')
        self.assertEqual(bound_mapping.readonly, True)
        self.assertEqual(bound_mapping.model_init, False)

    def test_foreign_key(self):
        mapping = Mapping('partner')
        bound_mapping = BoundMapping.bind_mapping(mapping, Person)

        self.assertEqual(bound_mapping.model, Person)
        self.assertEqual(bound_mapping.column_name, 'partner')
        self.assertEqual(bound_mapping.field_name, 'partner')
        self.assertEqual(bound_mapping.readonly, False)
        self.assertEqual(bound_mapping.model_init, True)
        self.assertEqual(bound_mapping.is_relationship, True)
        self.assertEqual(bound_mapping.is_foreign_key, True)

    def test_many_to_many(self):
        mapping = Mapping('children')
        bound_mapping = BoundMapping.bind_mapping(mapping, Person)

        self.assertEqual(bound_mapping.model, Person)
        self.assertEqual(bound_mapping.column_name, 'children')
        self.assertEqual(bound_mapping.field_name, 'children')
        self.assertEqual(bound_mapping.readonly, False)
        self.assertEqual(bound_mapping.model_init, False)
        self.assertEqual(bound_mapping.is_relationship, True)
        self.assertEqual(bound_mapping.is_one_to_many, True)