from io import StringIO
from json import dumps as json_dumps

from django.test import TestCase
from tablib import Dataset

from multi_import.exceptions import InvalidFileError
from multi_import.formats import json
from multi_import.helpers.files import decode_contents
from multi_import.helpers.files import read as multi_import_read


class JSONFormatTest(TestCase):
    def test_detect_valid_file(self):
        with open("tests/fixtures/test_file.json", "rb") as file:
            file.seek(0)
            file_contents = file.read()
            decoded_contents = decode_contents(file_contents)

            file_detection_result = json.detect(
                file_handler=file, file_contents=decoded_contents
            )

            self.assertTrue(file_detection_result)

    def test_detect_invalid_files(self):
        invalid_files = [
            "tests/fixtures/test_file.yaml",
            "tests/fixtures/test_file.csv",
            "tests/fixtures/test_file.xlsx",
        ]
        for invalid_file in invalid_files:
            with open(invalid_file, "rb") as file:
                file.seek(0)
                file_contents = file.read()
                decoded_contents = decode_contents(file_contents)

                file_detection_result = json.detect(
                    file_handler=file, file_contents=decoded_contents
                )

                self.assertFalse(
                    file_detection_result,
                    "Expected %s to be an invalid file" % invalid_file,
                )

    def test_read_valid_file(self):
        with open("tests/fixtures/test_file.json", "rb") as file:
            output = multi_import_read([json], file)

        expected_data = (
            "1",
            "c0eb1608-7a75-11ee-b962-0242ac120002",
            "Luke",
            "Lorem ipsum dolor sit",
            "Lorem ipsum dolor sit",
            "7",
            "c0eb1608-7a75-11ee-b962-0242ac120002",
            "1900-10-20T13:47:10-04:00",
            "1901-03-10T04:03:03.622000-05:00",
            "tea",
            "True",
            "tea",
            "c0eb1608-7a75-11ee-b962-0242ac120002",
            "1",
        )

        self.assertEqual(expected_data, output[0])

    def test_read_invalid_files(self):
        invalid_files = [
            "tests/fixtures/test_file.yaml",
            "tests/fixtures/test_file.csv",
            "tests/fixtures/test_file.xlsx",
        ]

        for invalid_file in invalid_files:
            with open(invalid_file, "rb") as file, self.assertRaises(InvalidFileError):
                multi_import_read([json], file)

    def test_key_property(self):
        self.assertEqual(json.key, "json")

    def test_extension_property(self):
        self.assertEqual(json.extension, "json")

    def test_pre_read(self):
        file_object = StringIO(json_dumps([{"name": "John", "age": 30}]))

        self.assertEqual(json.pre_read(file_object), file_object)

    def test_export_set(self):
        sample_data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]

        dataset = Dataset()
        dataset.dict = sample_data
        result = json.export_set(dataset)
        expected = json_dumps(
            sample_data,
            ensure_ascii=False,
            sort_keys=False,
            indent=2,
        )

        self.assertEqual(result, expected)
