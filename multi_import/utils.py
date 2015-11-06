import re

windows_line_ending = re.compile('\r\n?')


def normalize_string(input):
    value = input.strip()
    value = windows_line_ending.sub('\n', value)
    return value
