from django.test import TestCase

from multi_import.formats import CsvFormat
from multi_import.helpers.files import decode_contents


class FileDetect(TestCase):
    def get_file_and_decoded_contents(self, file_path):
        file = open(file_path, "rb")
        file.seek(0)
        file_contents = file.read()
        decoded_content = decode_contents(file_contents)

        return [file, decoded_content]


class CSVFileDetect(FileDetect):
    def test_json_file(self):
        file, decoded_contents = self.get_file_and_decoded_contents(
            "tests/test_import_files/test_file.json"
        )

        file_detection_result = CsvFormat().detect(
            file_handler=file, file_contents=decoded_contents
        )

        self.assertFalse(file_detection_result)

    def test_yaml_file(self):
        file, decoded_contents = self.get_file_and_decoded_contents(
            "tests/test_import_files/test_file.yaml"
        )

        file_detection_result = CsvFormat().detect(
            file_handler=file, file_contents=decoded_contents
        )

        self.assertFalse(file_detection_result)

    def test_csv_file(self):
        file, decoded_contents = self.get_file_and_decoded_contents(
            "tests/test_import_files/test_file.csv"
        )

        file_detection_result = CsvFormat().detect(
            file_handler=file, file_contents=decoded_contents
        )

        self.assertTrue(file_detection_result)

    def test_xlsx_file(self):
        file, decoded_contents = self.get_file_and_decoded_contents(
            "tests/test_import_files/test_file.xlsx"
        )

        file_detection_result = CsvFormat().detect(
            file_handler=file, file_contents=decoded_contents
        )

        self.assertFalse(file_detection_result)
