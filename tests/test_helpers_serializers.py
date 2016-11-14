from django.test import TestCase
from rest_framework.serializers import ModelSerializer

from multi_import.helpers import serializers
from multi_import.fields import LookupRelatedField

from tests.models import Book, Chapter, Person


class BookSerializer(ModelSerializer):

    class Meta:
        model = Book

        fields = (
            'id',
            'name',
            'author',
            'chapters',
        )

        read_only_fields = ('id', 'author')


class PersonSerializer(ModelSerializer):

    serializer_related_field = LookupRelatedField

    children = LookupRelatedField(
        many=True,
        default=[],
        lookup_fields=('first_name',),
        queryset=Person.objects.all()
    )

    class Meta:
        model = Person

        fields = (
            'id',
            'first_name',
            'last_name',
            'name',
            'partner',
            'children'
        )

        read_only_fields = ('id', 'name')


class SerializerHelperTests(TestCase):

    def test_returns_correct_dependencies(self):
        serializer = BookSerializer()
        dependencies = serializers.get_dependencies(serializer)
        self.assertEqual(dependencies, [Chapter])

    def test_returns_correct_related_fields(self):
        serializer = BookSerializer()
        fields = serializers.get_related_fields(serializer)

        self.assertEqual(fields[0].field_name, 'author')

    def test_returns_correct_many_related_fields(self):
        serializer = BookSerializer()
        fields = serializers.get_many_related_fields(serializer)

        self.assertEqual(fields[0].field_name, 'chapters')

    def test_might_have_changes_returns_false(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        serializer = PersonSerializer(justin, data={
            'first_name': 'Justin',
            'last_name': 'Trudeau',
            'partner': ''
        })

        might_have_changes = serializers.might_have_changes(serializer)
        self.assertFalse(might_have_changes)

    def test_might_have_changes_returns_true(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        serializer = PersonSerializer(justin, data={
            'first_name': 'Justin',
            'last_name': 'Trudeau2',
            'partner': ''
        })

        might_have_changes = serializers.might_have_changes(serializer)
        self.assertTrue(might_have_changes)

    def test_has_no_changes(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        serializer = PersonSerializer(justin, data={
            'first_name': 'Justin',
            'last_name': 'Trudeau',
            'partner': ''
        })

        serializer.is_valid()
        self.assertFalse(serializers.has_changes(serializer))

    def test_has_changes(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        serializer = PersonSerializer(justin, data={
            'first_name': 'Justin',
            'last_name': 'Trudeau2',
            'partner': ''
        })

        serializer.is_valid()
        self.assertTrue(serializers.has_changes(serializer))

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

        serializer = PersonSerializer()
        rep = serializer.to_representation(instance=justin)
        children = rep['children']

        self.assertEqual(children, [u'Hadrien', u'Xavier', u'Ella-Grace'])

    def test_get_diff_data_for_new_object(self):
        serializer = PersonSerializer(data={
            'first_name': 'Justin',
            'last_name': 'Trudeau',
            'partner': ''
        })

        serializer.is_valid()

        diff = serializers.get_diff_data(serializer)

        self.assertEqual(diff, {
            'first_name': ['', 'Justin'],
            'last_name': ['', 'Trudeau'],
            'partner': [''],
        })

    def test_get_diff_data_for_exisiting_object_with_no_changes(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        serializer = PersonSerializer(justin, data={
            'first_name': 'Justin',
            'last_name': 'Trudeau',
            'partner': ''
        })

        serializer.is_valid()

        diff = serializers.get_diff_data(serializer)

        self.assertEqual(diff, None)

    def test_get_diff_data_for_exisiting_object_with_changes(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        serializer = PersonSerializer(justin, data={
            'first_name': 'Justin',
            'last_name': 'Trudeau 2',
            'partner': ''
        })

        serializer.is_valid()

        diff = serializers.get_diff_data(serializer)

        self.assertEqual(diff, {
            'first_name': ['Justin'],
            'last_name': ['Trudeau', 'Trudeau 2'],
            'partner': [''],
        })
