from django.test import TestCase

from multi_import.object_cache import CachedObject, ObjectCache

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

        cache.cache_instance(obj)
        result = cache.get('arg1', 1, default)

        self.assertEqual(obj, result)

    def test_get__returns_default_for_no_match(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass()
        default = MyClass(1, 2)

        cache.cache_instance(obj)
        result = cache.get('arg1', None, default)

        self.assertEqual(default, result)

    def test_lookup(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass(1, 2)

        cache.cache_instance(obj)
        result = cache.lookup(lookup_fields, {'arg1': 1})

        self.assertEqual(obj, result)

    def test_lookup__value_pair(self):
        lookup_fields = ('arg1', ('arg2', 'arg3'))
        cache = ObjectCache(lookup_fields)
        obj1 = MyClass(1, 2, 3)
        obj2 = MyClass(1, 2, 4)
        obj3 = MyClass(1, 4, 3)

        cache.cache_instance(obj1)
        cache.cache_instance(obj2)
        cache.cache_instance(obj3)
        result = cache.lookup(lookup_fields, {'arg1': 2, 'arg2': 2, 'arg3': 3})

        self.assertEqual(obj1, result)

    def test_lookup__not_match(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass(1, 2)

        cache.cache_instance(obj)
        result = cache.lookup(lookup_fields, {'arg1': 2})

        self.assertIsNone(result)

    def test_lookup__multiple_results(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj1 = MyClass(1, 2)
        obj2 = MyClass(1, 3)

        cache.cache_instance(obj1)
        cache.cache_instance(obj2)

        with self.assertRaises(cache.multiple_objects_error):
            cache.lookup(lookup_fields, {'arg1': 1})

    def test_lookup_value(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass(1, 2)

        cache.cache_instance(obj)
        result = cache.lookup_value(1)

        self.assertEqual(obj, result)

    def test_lookup_value__value_pair(self):
        lookup_fields = ('arg1', ('arg2', 'arg3'))
        cache = ObjectCache(lookup_fields)
        obj1 = MyClass(1, 2, 3)
        obj2 = MyClass(1, 2, 4)
        obj3 = MyClass(1, 4, 3)

        cache.cache_instance(obj1)
        cache.cache_instance(obj2)
        cache.cache_instance(obj3)
        result = cache.lookup_value([2, 3])

        self.assertEqual(obj1, result)

    def test_lookup_value__value_pair_not_found(self):
        lookup_fields = ('arg1', ('arg2', 'arg3'))
        cache = ObjectCache(lookup_fields)
        obj1 = MyClass(1, 2, 3)
        obj2 = MyClass(1, 2, 4)
        obj3 = MyClass(1, 4, 3)

        cache.cache_instance(obj1)
        cache.cache_instance(obj2)
        cache.cache_instance(obj3)
        result = cache.lookup_value([1, 3])

        self.assertIsNone(result)

    def test_lookup_value__not_found(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj = MyClass(1, 2)

        cache.cache_instance(obj)
        result = cache.lookup_value(2)

        self.assertIsNone(result)

    def test_lookup_value__multiple_results(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)
        obj1 = MyClass(1, 2)
        obj2 = MyClass(1, 3)

        cache.cache_instance(obj1)
        cache.cache_instance(obj2)

        with self.assertRaises(cache.multiple_objects_error):
            cache.lookup_value(1)

    def test_len(self):
        lookup_fields = ('arg1',)
        cache = ObjectCache(lookup_fields)

        for i in range(1, 10):
            obj = MyClass(i)
            cache.cache_instance(obj)
            self.assertEqual(len(cache), i)
