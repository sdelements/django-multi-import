from django.test import TestCase
from multi_import.relations import LookupRelatedField
from multi_import.serializers import ModelSerializer

from tests.models import Person


class PersonSerializer(ModelSerializer):

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


class ModelSerializerTests(TestCase):

    def test_has_no_changes(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        serializer = PersonSerializer(justin, data={
            'first_name': 'Justin',
            'last_name': 'Trudeau',
            'partner': None
        })

        serializer.is_valid()
        self.assertFalse(serializer.has_changes)

    def test_has_changes(self):
        justin = Person(first_name='Justin', last_name='Trudeau')
        justin.save()

        serializer = PersonSerializer(justin, data={
            'first_name': 'Justin',
            'last_name': 'Trudeau2',
            'partner': None
        })

        serializer.is_valid()
        self.assertTrue(serializer.has_changes)

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
