from django.test import TestCase

from multi_import.mappings import Mapping, BoundMapping
from multi_import.value_resolver import ValueResolver, ResolvedValue
from tests.models import Person


def get_mapping(*args, **kwargs):
    mapping = Mapping(*args, **kwargs)
    return BoundMapping(mapping, Person)


def get_value_resolver(*args, **kwargs):
    bound_mapping = get_mapping(*args, **kwargs)
    return ValueResolver(bound_mapping)


class ResolvedValueTests(TestCase):

    def test_none(self):
        expected = ''

        mapping = get_mapping('first_name')
        resolved_value = ResolvedValue(mapping, None)
        result = resolved_value.get_string()

        self.assertEqual(result, expected)

    def test_string(self):
        expected = 'Justin'

        mapping = get_mapping('first_name')
        resolved_value = ResolvedValue(mapping, 'Justin')
        result = resolved_value.get_string()

        self.assertEqual(result, expected)

    def test_number(self):
        expected = '6'

        mapping = get_mapping('first_name')
        resolved_value = ResolvedValue(mapping, 6)
        result = resolved_value.get_string()

        self.assertEqual(result, expected)

    def test_foreign_key(self):
        sophie = Person(first_name='Sophie', last_name='Gregoire')
        sophie.save()
        expected = str(sophie.pk)

        mapping = get_mapping('partner')
        resolved_value = ResolvedValue(mapping, sophie)
        result = resolved_value.get_string()

        self.assertEqual(result, expected)

    def test_foreign_key_with_custom_lookup_field(self):
        sophie = Person(first_name='Sophie', last_name='Gregoire')
        sophie.save()
        expected = 'Sophie Gregoire'

        mapping = get_mapping('partner', lookup_fields=('name',))
        resolved_value = ResolvedValue(mapping, sophie)
        result = resolved_value.get_string()

        self.assertEqual(result, expected)

    def test_one_to_many(self):
        list_separator = '|'

        children = [
            Person(first_name='Hadrien', last_name='Trudeau'),
            Person(first_name='Xavier', last_name='Trudeau'),
            Person(first_name='Ella-Grace', last_name='Trudeau')
        ]

        for child in children:
            child.save()

        expected = list_separator.join([str(child.pk) for child in children])

        mapping = get_mapping('children', list_separator=list_separator)
        resolved_value = ResolvedValue(mapping, children)
        result = resolved_value.get_string()

        self.assertEqual(result, expected)


class ValueResolverTests(TestCase):

    def test_export_simple_field(self):
        justin = Person(first_name='Justin', last_name='Trudeau')

        value_resolver = get_value_resolver('first_name')
        resolved_value = value_resolver.resolve_export_value(justin)

        self.assertEqual('Justin', resolved_value.value)

    def test_export_property(self):
        justin = Person(first_name='Justin', last_name='Trudeau')

        value_resolver = get_value_resolver('name')
        resolved_value = value_resolver.resolve_export_value(justin)

        self.assertEqual('Justin Trudeau', resolved_value.value)

    def test_export_foreign_key(self):
        sophie = Person(first_name='Sophie', last_name='Gregoire')
        sophie.save()

        justin = Person(first_name='Justin', last_name='Trudeau',
                        partner=sophie)

        value_resolver = get_value_resolver('partner')
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

        value_resolver = get_value_resolver('children')
        resolved_value = value_resolver.resolve_export_value(justin)

        self.assertEqual([hadrien, xavier, ella_grace], resolved_value.value)

    def test_import_simple_field(self):
        data = {'first_name': 'Justin'}

        value_resolver = get_value_resolver('first_name')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual('Justin', resolved_value.value)

    def test_import_simple_field_custom_column(self):
        data = {'name': 'Justin'}

        value_resolver = get_value_resolver('name', 'first_name')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual('Justin', resolved_value.value)

    def test_import_foreign_key(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        data = {'partner': str(justin.pk)}

        value_resolver = get_value_resolver('partner')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual(justin, resolved_value.value)

    def test_import_foreign_key_not_given(self):
        value_resolver = get_value_resolver('partner')
        resolved_value = value_resolver.resolve_import_value()

        self.assertEqual(None, resolved_value.value)

    def test_import_foreign_key_does_not_exist(self):
        data = {'partner': '6'}

        value_resolver = get_value_resolver('partner')
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

        children = '{0};{1};{2}'.format(hadrien.pk, xavier.pk, ella_grace.pk)
        data = {'children': children}

        value_resolver = get_value_resolver('children')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual([hadrien, xavier, ella_grace], resolved_value.value)

    def test_import_one_to_many_not_given(self):
        value_resolver = get_value_resolver('children')
        resolved_value = value_resolver.resolve_import_value()

        self.assertEqual([], resolved_value.value)

    def test_import_one_to_many_do_not_exist(self):
        data = {'children': '6'}

        value_resolver = get_value_resolver('children')
        resolved_value = value_resolver.resolve_import_value(data)

        self.assertEqual(['No match found for: 6'], resolved_value.errors)
        self.assertEqual([], resolved_value.value)

    def test_import_one_to_many_do_not_exist_2(self):
        data = {'children': '6;4'}

        value_resolver = get_value_resolver('children')
        resolved_value = value_resolver.resolve_import_value(data)

        expected_errors = ['No match found for: 6', 'No match found for: 4']

        self.assertEqual(expected_errors, resolved_value.errors)
        self.assertEqual([], resolved_value.value)
