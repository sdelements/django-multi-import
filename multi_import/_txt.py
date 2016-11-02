# -*- coding: utf-8 -*-

from tablib.compat import is_py3, StringIO


title = 'txt'
extensions = ('txt',)


DEFAULT_ENCODING = 'utf-8'


def export_set(dataset, **kwargs):
    """Returns text representation of Dataset."""
    stream = StringIO()

    if not is_py3:
        kwargs.setdefault('encoding', DEFAULT_ENCODING)

    for row in dataset._package():
        for key, val in row.iteritems():
            stream.write('-' * len(key) + '\n')
            stream.write(key.encode('utf-8') + '\n')
            stream.write('-' * len(key) + '\n')
            stream.write(val.encode('utf-8') + '\n\n')
        stream.write('\n' + '*' * 50 + '\n\n\n')

    return stream.getvalue()


def import_set(dset, in_stream, headers=True, **kwargs):
    return NotImplementedError


def detect(stream):
    return False
