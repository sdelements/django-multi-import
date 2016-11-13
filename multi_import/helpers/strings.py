import re

windows_line_ending = re.compile('\r\n?')


def normalize_string(s):
    value = s.strip()
    value = windows_line_ending.sub('\n', value)
    return value


def excel_escape(s):
    """
    This escape method will prevent Excel macro injection.
    When excel sees a space, it treats the contents as a string,
    therefore preventing formulas from running.
    """
    blacklist = ['=', '+', '-', '@']

    if s and s[0] in blacklist:
        s = ' ' + s

    return s
