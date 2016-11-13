from django.test import TestCase

from multi_import.cache import CachedObject, ObjectCache

from tests.models import Book


class MyClass(object):
    def __init__(self, arg1=None, arg2=None, arg3=None):
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3


class CachedObjectTests(TestCase):

    def test_hash__plain_object(self):
        obj = MyClass(1, 2)
        cached_obj = CachedObject(obj)

        self.assertEqual(obj.__hash__(), cached_obj.__hash__())
        self.assertEqual(obj, cached_obj.obj)

    def test_hash__model_unsaved(self):
        obj = Book()
        cached_obj = CachedObject(obj)

        self.assertEqual(obj, cached_obj.obj)

        with self.assertRaises(TypeError):
            obj.__hash__()

        # Returns with no exception
        cached_obj.__hash__()


class ObjectCacheTests(TestCase):

    def test_get(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass(1, 2)
        default = MyClass()

        cache.add(obj)
        result = cache.get('arg1', 1, default)

        self.assertEqual(obj, result)

    def test_get__returns_default_for_no_match(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass()
        default = MyClass(1, 2)

        cache.add(obj)
        result = cache.get('arg1', None, default)

        self.assertEqual(default, result)

    def test_find(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass(1, 2)

        cache.add(obj)
        result = cache.find(1)

        self.assertEqual(obj, result)

    def test_find__not_found(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass(1, 2)

        cache.add(obj)
        result = cache.find(2)

        self.assertIsNone(result)

    def test_find__multiple_results(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj1 = MyClass(1, 2)
        obj2 = MyClass(1, 3)

        cache.add(obj1)
        cache.add(obj2)

        with self.assertRaises(cache.multiple_objects_error):
            cache.find(1)

    def test_match(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass(1, 2)

        cache.add(obj)
        result = cache.match({'arg1': 1})

        self.assertEqual(obj, result)

    def test_match__value_pair(self):
        lookup_fields = ('arg1', ('arg2', 'arg3'))
        cache = ObjectCache(lookup_fields)
        obj1 = MyClass(1, 2, 3)
        obj2 = MyClass(1, 2, 4)
        obj3 = MyClass(1, 4, 3)

        cache.add(obj1)
        cache.add(obj2)
        cache.add(obj3)
        result = cache.match({'arg1': 2, 'arg2': 2, 'arg3': 3})

        self.assertEqual(obj1, result)

    def test_match__not_match(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass(1, 2)

        cache.add(obj)
        result = cache.match({'arg1': 2})

        self.assertIsNone(result)

    def test_match__multiple_results(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj1 = MyClass(1, 2)
        obj2 = MyClass(1, 3)

        cache.add(obj1)
        cache.add(obj2)

        with self.assertRaises(cache.multiple_objects_error):
            cache.match({'arg1': 1})

    def test_len(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)

        for i in range(1, 10):
            obj = MyClass(i)
            cache.add(obj)
            self.assertEqual(len(cache), i)
