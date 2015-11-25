from django.test import TestCase

from multi_import.mappings import Mapping, BoundMapping, MappingCollection
from tests.models import Person


class MappingTests(TestCase):

    def test_simple_field(self):
        mapping = Mapping('first_name')
        bound_mapping = BoundMapping.bind_mapping(mapping, Person)

        self.assertIsInstance(bound_mapping, BoundMapping)
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


class MappingCollectionTests(TestCase):

    def test_mapping_collection(self):
        mappings = Mapping('first_name'), Mapping('last_name')
        bound_mappings = BoundMapping.bind_mappings(mappings, Person)

        self.assertIsInstance(bound_mappings, MappingCollection)
        self.assertEqual(len(bound_mappings), 2)

    def test_fields(self):
        mappings = Mapping('first_name'), Mapping('last_name')
        bound_mappings = BoundMapping.bind_mappings(mappings, Person)
        fields_dict = bound_mappings.fields

        self.assertIsInstance(fields_dict, dict)
        self.assertEqual(len(fields_dict), 2)

    def test_columns(self):
        mappings = Mapping('first_name'), Mapping('last_name')
        bound_mappings = BoundMapping.bind_mappings(mappings, Person)
        columns_dict = bound_mappings.columns

        self.assertIsInstance(columns_dict, dict)
        self.assertEqual(len(columns_dict), 2)

    def test_column_names(self):
        mappings = Mapping('first_name'), Mapping('last_name')
        bound_mappings = BoundMapping.bind_mappings(mappings, Person)
        column_names = bound_mappings.column_names

        self.assertIsInstance(column_names, list)
        self.assertEqual(len(column_names), 2)

    def test_writable(self):
        mappings = Mapping('first_name'), Mapping('last_name'), Mapping('name')
        bound_mappings = BoundMapping.bind_mappings(mappings, Person)

        self.assertIsInstance(bound_mappings, MappingCollection)
        self.assertEqual(len(bound_mappings), 3)

        writable = bound_mappings.writable

        self.assertIsInstance(writable, MappingCollection)
        self.assertEqual(len(writable), 2)

    def test_filter_by_column_names(self):
        mappings = Mapping('first_name'), Mapping('last_name')
        bound_mappings = BoundMapping.bind_mappings(mappings, Person)
        filtered_mappings = bound_mappings.filter_by_columns(['first_name'])

        self.assertIsInstance(filtered_mappings, MappingCollection)
        self.assertEqual(len(filtered_mappings), 1)
