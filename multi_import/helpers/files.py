import tablib
from django.utils.translation import ugettext_lazy as _

from multi_import.exceptions import InvalidFileError
from multi_import.formats import FileFormat


def find_format(file_formats, file_format=None):
    if isinstance(file_format, FileFormat):
        return file_format

    return next(
        (f for f in file_formats if f.key == file_format),
        file_formats[0]
    )


def read(file_formats, file):
    file.seek(0)
    file_contents = file.read()

    for file_format in file_formats:
        try:
            if file_format.detect(file, file_contents):
                return file_format.read(file, file_contents)

        except AttributeError:
            pass

        except (tablib.InvalidDimensions, tablib.UnsupportedFormat):
            raise InvalidFileError(_(u'Empty or Invalid File.'))

    raise InvalidFileError(_(u'Invalid File Type.'))
