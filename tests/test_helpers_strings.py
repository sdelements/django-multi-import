from django.test import TestCase

from multi_import.helpers import strings


class StringHelperTests(TestCase):

    def test_normalize_string(self):
        value_pairs = (
            ('  HELLO\r\nWORLD  ', 'HELLO\nWORLD'),
            ('  HELLO\n\rWORLD  ', 'HELLO\n\nWORLD'),
        )

        for value, expected in value_pairs:
            actual = strings.normalize_string(value)
            self.assertEqual(expected, actual)

    def test_excel_escape(self):
        value_pairs = (
            ('1', '1'),
            ('=1', ' =1'),
            ('+1', ' +1'),
            ('-1', ' -1'),
            ('@1', ' @1'),
        )

        for value, expected in value_pairs:
            actual = strings.excel_escape(value)
            self.assertEqual(expected, actual)
