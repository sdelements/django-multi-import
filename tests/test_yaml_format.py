from io import StringIO

import yaml as pyyaml
from django.test import TestCase
from tablib import Dataset

from multi_import.exceptions import InvalidFileError
from multi_import.formats import yaml
from multi_import.helpers.files import decode_contents
from multi_import.helpers.files import read as multi_import_read

try:
    from yaml import CSafeDumper
except ImportError:
    CSafeDumper = None


class YAMLFormatTest(TestCase):
    def test_detect_valid_file(self):
        with open("tests/fixtures/test_file.yaml", "rb") as file:
            file.seek(0)
            file_contents = file.read()
            decoded_contents = decode_contents(file_contents)

            file_detection_result = yaml.detect(
                file_handler=file, file_contents=decoded_contents
            )

            self.assertTrue(file_detection_result)

    def test_detect_json_file(self):
        """
        YAML is a superset of the JSON format so it can handle JSON files.
        """
        with open("tests/fixtures/test_file.json", "rb") as file:
            file.seek(0)
            file_contents = file.read()
            decoded_contents = decode_contents(file_contents)

            file_detection_result = yaml.detect(
                file_handler=file, file_contents=decoded_contents
            )

            self.assertTrue(file_detection_result)

    def test_detect_invalid_files(self):
        invalid_files = [
            "tests/fixtures/test_file.xlsx",
            "tests/fixtures/test_file.csv",
        ]
        for invalid_file in invalid_files:
            with open(invalid_file, "rb") as file:
                file.seek(0)
                file_contents = file.read()
                decoded_contents = decode_contents(file_contents)

                file_detection_result = yaml.detect(
                    file_handler=file, file_contents=decoded_contents
                )

                self.assertFalse(
                    file_detection_result,
                    "Expected %s to be an invalid file" % invalid_file,
                )

    def test_read_valid_file(self):
        """
        YAML is a superset of the JSON format so it can handle JSON files.
        """
        with open("tests/fixtures/test_file.yaml", "rb") as file:
            output = multi_import_read([yaml], file)

        expected_data = (
            1,
            "c0eb1608-7a75-11ee-b962-0242ac120002",
            "student",
            "1",
            "False",
            "",
            "",
        )

        self.assertEqual(expected_data, output[0])

    def test_read_json_file(self):
        with open("tests/fixtures/test_file.json", "rb") as file:
            output = multi_import_read([yaml], file)

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
            "tests/fixtures/test_file.xlsx",
            "tests/fixtures/test_file.csv",
        ]

        for invalid_file in invalid_files:
            with open(invalid_file, "rb") as file, self.assertRaises(InvalidFileError):
                multi_import_read([yaml], file)

    def test_key_property(self):
        self.assertEqual(yaml.key, "yaml")

    def test_extension_property(self):
        self.assertEqual(yaml.extension, "yaml")

    def test_pre_read(self):
        file_object = StringIO(pyyaml.dump([{"name": "John", "age": 30}]))

        self.assertEqual(yaml.pre_read(file_object), file_object)

    def test_export_set(self):
        sample_data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]

        dataset = Dataset()
        dataset.dict = sample_data
        result = yaml.export_set(dataset)
        if CSafeDumper:
            expected = pyyaml.dump(
                sample_data,
                Dumper=CSafeDumper,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        else:
            expected = pyyaml.safe_dump(
                sample_data,
                Dumper=pyyaml.SafeDumper,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

        self.assertEqual(result, expected)
