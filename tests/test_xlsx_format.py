from django.test import TestCase

from multi_import.exceptions import InvalidFileError
from multi_import.formats import xlsx
from multi_import.helpers.files import decode_contents, read as multi_import_read


class XLSXFormatTest(TestCase):
    def test_detect_valid_file(self):
        with open("tests/fixtures/test_file.xlsx", "rb") as file:
            file.seek(0)
            file_contents = file.read()
            decoded_contents = decode_contents(file_contents)

            file_detection_result = xlsx.detect(
                file_handler=file, file_contents=decoded_contents
            )

            self.assertTrue(file_detection_result)

    def test_detect_invalid_files(self):
        invalid_files = [
            "tests/fixtures/test_file.yaml",
            "tests/fixtures/test_file.csv",
            "tests/fixtures/test_file.json"
        ]
        for invalid_file in invalid_files:
            with open(invalid_file, "rb") as file:
                file.seek(0)
                file_contents = file.read()
                decoded_contents = decode_contents(file_contents)

                file_detection_result = xlsx.detect(
                    file_handler=file, file_contents=decoded_contents
                )

                self.assertFalse(file_detection_result, "Expected %s to be an invalid file" % invalid_file)

    def test_read_valid_file(self):
        with open("tests/fixtures/test_file.xlsx", "rb") as file:
            output = multi_import_read([xlsx], file)

        expected_data = (1, 'c0eb1608-7a75-11ee-b962-0242ac120002', 'Lorem', 'Lorem', 'ipsum', 2, 'i[sum', '1900-10-20T13:47:10-04:00', '1901-03-10T04:03:03.622000-05:00', 'ice tea', 'True', 'ice tea', 'c0eb1608-7a75-11ee-b962-0242ac120002', 1)

        self.assertEqual(expected_data, output[0])

    def test_read_invalid_files(self):
        invalid_files = [
            "tests/fixtures/test_file.yaml",
            "tests/fixtures/test_file.csv",
            "tests/fixtures/test_file.json"
        ]

        for invalid_file in invalid_files:
            with open(invalid_file, "rb") as file, self.assertRaises(
                InvalidFileError
            ):
                multi_import_read([xlsx], file)
