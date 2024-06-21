from django.test import TestCase

from multi_import.exceptions import InvalidFileError
from multi_import.formats import csv
from multi_import.helpers.files import decode_contents
from multi_import.helpers.files import read as multi_import_read


class CSVFormatTest(TestCase):
    def test_detect_csv_file(self):
        with open("tests/fixtures/test_file.csv", "rb") as file:
            file.seek(0)
            file_contents = file.read()
            decoded_contents = decode_contents(file_contents)

            file_detection_result = csv.detect(
                file_handler=file, file_contents=decoded_contents
            )

            self.assertTrue(file_detection_result)

    def test_detect_invalid_csv_files(self):
        invalid_files = [
            "tests/fixtures/test_file.yaml",
            "tests/fixtures/test_file.json",
            "tests/fixtures/test_file.xlsx",
        ]
        for invalid_file in invalid_files:
            with open(invalid_file, "rb") as file:
                file.seek(0)
                file_contents = file.read()
                decoded_contents = decode_contents(file_contents)

                file_detection_result = csv.detect(
                    file_handler=file, file_contents=decoded_contents
                )

                self.assertFalse(
                    file_detection_result,
                    "Expected %s to be an invalid file" % invalid_file,
                )

    def test_read_csv_file(self):
        with open("tests/fixtures/test_file.csv", "rb") as file:
            output = multi_import_read([csv], file)

        expected_data = (
            "1",
            "c0eb1608-7a75-11ee-b962-0242ac120002",
            "Jedi",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
            "lorem",
            "1",
            "00c5755c-7a76-11ee-b962-0242ac120002",
            "1900-11-20T13:47:10-04:00",
            "1900-11-20T13:47:10-04:00",
            "mocha",
            "True",
            "mocha",
            "00c5755c-7a76-11ee-b962-0242ac120002",
            "lorem",
            "",
            "",
            "",
            "",
        )

        self.assertEqual(expected_data, output[0])

    def test_read_invalid_csv_files(self):
        invalid_files = [
            "tests/fixtures/test_file.yaml",
            "tests/fixtures/test_file.json",
            "tests/fixtures/test_file.xlsx",
        ]

        for invalid_file in invalid_files:
            with open(invalid_file, "rb") as file, self.assertRaises(InvalidFileError):
                multi_import_read([csv], file)
