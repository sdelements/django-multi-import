# -*- coding: utf-8 -*-
import chardet
from django.test import TestCase
from six import BytesIO

from multi_import.helpers import files


class FileHelperTests(TestCase):

    def test_decode_file_when_reading_utf_8(self):
        file = BytesIO()
        file.write(u'UTF-8 character: Đà'.encode('utf-8'))

        file.seek(0)
        file_contents = file.read()
        charset = chardet.detect(file_contents)
        encoding = charset['encoding']

        self.assertEqual('utf-8', encoding)

        decoded_file_contents = files.decode_contents(file_contents)
        self.assertTrue(type(decoded_file_contents), str)

    def test_decode_file_when_reading_utf_16(self):
        file = BytesIO()
        file.write(u'UTF-16 character: $'.encode('utf-16'))

        file.seek(0)
        file_contents = file.read()
        charset = chardet.detect(file_contents)
        encoding = charset['encoding']

        self.assertEqual('UTF-16', encoding)

        decoded_file_contents = files.decode_contents(file_contents)
        self.assertTrue(type(decoded_file_contents), str)

    def test_decode_file_when_reading_iso_8859_1(self):
        file = BytesIO()
        file.write(u'Latin-1 character: ¥'.encode('ISO-8859-1'))

        file.seek(0)
        file_contents = file.read()
        charset = chardet.detect(file_contents)
        encoding = charset['encoding']

        # Latin-1 and ISO-8859-1 are equivalent.
        self.assertEqual('ISO-8859-1', encoding)

        decoded_file_contents = files.decode_contents(file_contents)
        self.assertTrue(type(decoded_file_contents), str)
