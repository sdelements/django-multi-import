from django.test import TestCase

from multi_import.mappings import Mapping, BoundMapping
from multi_import.value_resolver import ValueResolver
from tests.models import Person


class ValueResolverTests(TestCase):

    def get_value_resolver(self, *args, **kwargs):
        mapping = Mapping(*args, **kwargs)
        bound_mapping = BoundMapping(mapping, Person)
        return ValueResolver(bound_mapping)

    def test_export_simple_field(self):
        justin = Person(first_name='Justin', last_name='Trudeau')

        value_resolver = self.get_value_resolver('first_name')
        resolved_value = value_resolver.resolve_export_value(justin)

        self.assertEqual('Justin', resolved_value.value)

    def test_export_property(self):
        justin = Person(first_name='Justin', last_name='Trudeau')

        value_resolver = self.get_value_resolver('name')
        resolved_value = value_resolver.resolve_export_value(justin)

        self.assertEqual('Justin Trudeau', resolved_value.value)

    def test_export_foreign_key(self):
        sophie = Person(first_name='Sophie', last_name='Gregoire')
        justin = Person(first_name='Justin', last_name='Trudeau', partner=sophie)

        value_resolver = self.get_value_resolver('partner')
        resolved_value = value_resolver.resolve_export_value(justin)

        self.assertEqual(sophie, resolved_value.value)

    def test_export_one_to_many(self):
        hadrien = Person(first_name='Hadrien', last_name='Trudeau')
        xavier = Person(first_name='Xavier', last_name='Trudeau')
        ella_grace = Person(first_name='Ella-Grace', last_name='Trudeau')
        justin = Person(first_name='Justin', last_name='Trudeau')

        hadrien.save()
        xavier.save()
        ella_grace.save()
        justin.save()

        justin.children.add(hadrien)
        justin.children.add(xavier)
        justin.children.add(ella_grace)

        justin.save()

        value_resolver = self.get_value_resolver('children')
        resolved_value = value_resolver.resolve_export_value(justin)

        self.assertEqual([hadrien, xavier, ella_grace], resolved_value.value)

    def test_import_simple_field(self):
        data = {'first_name': 'Justin'}

        value_resolver = self.get_value_resolver('first_name')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual('Justin', resolved_value.value)

    def test_import_simple_field_custom_column(self):
        data = {'name': 'Justin'}

        value_resolver = self.get_value_resolver('name', 'first_name')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual('Justin', resolved_value.value)

    def test_import_foreign_key(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        data = {'partner': str(justin.pk)}

        value_resolver = self.get_value_resolver('partner')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual(justin, resolved_value.value)

    def test_import_foreign_key_not_given(self):
        value_resolver = self.get_value_resolver('partner')
        resolved_value = value_resolver.resolve_import_value()

        self.assertEqual(None, resolved_value.value)

    def test_import_foreign_key_does_not_exist(self):
        data = {'partner': '6'}

        value_resolver = self.get_value_resolver('partner')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual(['No match found for: 6'], resolved_value.errors)
        self.assertEqual(None, resolved_value.value)

    def test_import_one_to_many(self):
        hadrien = Person(first_name='Hadrien', last_name='Trudeau')
        xavier = Person(first_name='Xavier', last_name='Trudeau')
        ella_grace = Person(first_name='Ella-Grace', last_name='Trudeau')

        hadrien.save()
        xavier.save()
        ella_grace.save()

        data = {'children': '{0},{1},{2}'.format(hadrien.pk, xavier.pk, ella_grace.pk)}

        value_resolver = self.get_value_resolver('children')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual([hadrien, xavier, ella_grace], resolved_value.value)

    def test_import_one_to_many_not_given(self):
        value_resolver = self.get_value_resolver('children')
        resolved_value = value_resolver.resolve_import_value()

        self.assertEqual([], resolved_value.value)

    def test_import_one_to_many_do_not_exist(self):
        data = {'children': '6'}

        value_resolver = self.get_value_resolver('children')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual(['No match found for: 6'], resolved_value.errors)
        self.assertEqual([], resolved_value.value)

    def test_import_one_to_many_do_not_exist_2(self):
        data = {'children': '6,4'}

        value_resolver = self.get_value_resolver('children')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual(['No match found for: 6', 'No match found for: 4'], resolved_value.errors)
        self.assertEqual([], resolved_value.value)
