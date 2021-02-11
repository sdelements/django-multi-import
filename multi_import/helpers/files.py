import tablib
from django.utils.translation import ugettext_lazy as _

from multi_import.exceptions import InvalidFileError
from multi_import.formats import FileFormat


def find_format(file_formats, file_format=None):
    if isinstance(file_format, FileFormat):
        return file_format

    return next((f for f in file_formats if f.key == file_format), file_formats[0])


def decode_contents(file_contents):
    encodings = ["UTF-8", "UTF-16", "ISO-8859-1"]

    for encoding in encodings:
        try:
            return file_contents.decode(encoding)
        except UnicodeDecodeError:
            pass

    raise InvalidFileError(_(u"File encoding not identified."))


def read(file_formats, file):
    import_file_formats = [f for f in file_formats if not f.read_only]

    supported_content_types = [f.content_type for f in import_file_formats]

    # When Content-Type unspecified, defaults to this.
    # https://sdelements.atlassian.net/browse/LIBR-355
    # https://stackoverflow.com/questions/12061030/why-am-i-getting-mime-type-of-csv-file-as-application-octet-stream
    supported_content_types.append("application/octet-stream")

    # IE sends this for CSV files
    supported_content_types.append("text/plain")

    if file.content_type not in supported_content_types:
        allowed_extensions = ", ".join(
            [f.extension.upper() for f in import_file_formats]
        )
        msg = _(
            u"{0} file types are not supported. Please upload a file with one of the following formats: {1}."
        ).format(file.content_type, allowed_extensions)
        raise InvalidFileError(msg)

    file.seek(0)
    file_contents = file.read()
    decoded_file_contents = decode_contents(file_contents)

    for file_format in file_formats:
        try:
            if file_format.detect(file, decoded_file_contents):
                return file_format.read(file, decoded_file_contents)

        except AttributeError:
            pass

        except tablib.InvalidDimensions:
            raise InvalidFileError(
                _(
                    u"File must not be empty, "
                    u"and all rows must have same columns/properties."
                )
            )

        except tablib.UnsupportedFormat:
            raise InvalidFileError(_(u"Invalid File."))

    raise InvalidFileError(_(u"Invalid File Type."))
