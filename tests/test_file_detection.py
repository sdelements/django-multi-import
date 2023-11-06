from django.test import TestCase

from multi_import.formats import CsvFormat
from multi_import.helpers.files import decode_contents


class CSVFileDetect(TestCase):
    def test_json_file(self):
        with open("tests/test_import_files/test_file.json", "rb") as file:
            file.seek(0)
            file_contents = file.read()
            decoded_contents = decode_contents(file_contents)

            file_detection_result = CsvFormat().detect(
                file_handler=file, file_contents=decoded_contents
            )

            self.assertFalse(file_detection_result)

    def test_yaml_file(self):
        with open("tests/test_import_files/test_file.yaml", "rb") as file:
            file.seek(0)
            file_contents = file.read()
            decoded_contents = decode_contents(file_contents)

            file_detection_result = CsvFormat().detect(
                file_handler=file, file_contents=decoded_contents
            )

            self.assertFalse(file_detection_result)

    def test_csv_file(self):
        with open("tests/test_import_files/test_file.csv", "rb") as file:
            file.seek(0)
            file_contents = file.read()
            decoded_contents = decode_contents(file_contents)

            file_detection_result = CsvFormat().detect(
                file_handler=file, file_contents=decoded_contents
            )

            self.assertTrue(file_detection_result)

    def test_xlsx_file(self):
        with open("tests/test_import_files/test_file.xlsx", "rb") as file:
            file.seek(0)
            file_contents = file.read()
            decoded_contents = decode_contents(file_contents)

            file_detection_result = CsvFormat().detect(
                file_handler=file, file_contents=decoded_contents
            )

            self.assertFalse(file_detection_result)
