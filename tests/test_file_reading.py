from django.test import TestCase

from multi_import.exceptions import InvalidFileError
from multi_import.formats import csv, json, xlsx, yaml
from multi_import.helpers.files import read as multi_import_read


class CSVFileRead(TestCase):
    def test_json_file(self):
        with open("tests/fixtures/test_file.json", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([csv], file)

    def test_yaml_file(self):
        with open("tests/fixtures/test_file.yaml", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([csv], file)

    def test_csv_file(self):
        with open("tests/fixtures/test_file.csv", "rb") as file:
            multi_import_read([csv], file)

    def test_xlsx_file(self):
        with open("tests/fixtures/test_file.xlsx", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([csv], file)


class XLSXFileRead(TestCase):
    def test_json_file(self):
        with open("tests/fixtures/test_file.json", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([xlsx], file)

    def test_yaml_file(self):
        with open("tests/fixtures/test_file.yaml", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([xlsx], file)

    def test_csv_file(self):
        with open("tests/fixtures/test_file.csv", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([xlsx], file)

    def test_xlsx_file(self):
        with open("tests/fixtures/test_file.xlsx", "rb") as file:
            multi_import_read([xlsx], file)


class JSONFileRead(TestCase):
    def test_json_file(self):
        with open("tests/fixtures/test_file.json", "rb") as file:
            multi_import_read([json], file)

    def test_yaml_file(self):
        with open("tests/fixtures/test_file.yaml", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([json], file)

    def test_csv_file(self):
        with open("tests/fixtures/test_file.csv", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([json], file)

    def test_xlsx_file(self):
        with open("tests/fixtures/test_file.xlsx", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([json], file)


class YAMLFileRead(TestCase):
    def test_json_file(self):
        # YAML is a superset of the JSON format and thus can be used to read JSON files
        with open("tests/fixtures/test_file.json", "rb") as file:
            multi_import_read([yaml], file)

    def test_yaml_file(self):
        with open("tests/fixtures/test_file.yaml", "rb") as file:
            multi_import_read([yaml], file)

    def test_csv_file(self):
        with open("tests/fixtures/test_file.csv", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([yaml], file)

    def test_xlsx_file(self):
        with open("tests/fixtures/test_file.xlsx", "rb") as file, self.assertRaises(
            InvalidFileError
        ):
            multi_import_read([yaml], file)
