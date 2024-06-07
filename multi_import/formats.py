from csv import Error as NullError
from io import BytesIO, StringIO

import chardet
from django.utils.translation import gettext_lazy as _
from tablib import detect_format
from tablib.core import Dataset, InvalidDimensions, UnsupportedFormat
from tablib.formats import _csv, _json, _xls, _xlsx, _yaml

try:
    from yaml import CSafeDumper
except ImportError:
    CSafeDumper = None

from multi_import.exceptions import InvalidFileError
from multi_import.helpers import strings


class FileFormat(object):
    title = None

    @property
    def key(self):
        return self.title

    @property
    def extension(self):
        return self.key

    def detect(self, file_handler, file_contents):
        return False

    def pre_read(self, file_object):
        return file_object

    def read(self, file_handler, file_contents):
        raise NotImplementedError()

    def write(self, dataset):
        raise NotImplementedError()


class TabLibFileFormat(FileFormat):
    def __init__(
        self,
        file_format,
        content_type,
        read_file_as_string=False,
        empty_file_requires_example_row=False,
    ):
        self.format = file_format
        self.content_type = content_type
        self.read_file_as_string = read_file_as_string
        self.empty_file_requires_example_row = empty_file_requires_example_row

    @property
    def key(self):
        return self.format.title

    def get_file_object(self, file_handler, file_contents):
        if self.read_file_as_string:
            return file_contents

        file_handler.seek(0)
        return file_handler

    def detect(self, file_handler, file_contents):
        file_object = self.get_file_object(file_handler, file_contents)
        try:
            return detect_format(file_object)
        except AttributeError:
            pass
        return False

    def pre_read(self, file_object):
        return file_object

    def read(self, file_handler, file_contents):
        file_object = self.get_file_object(file_handler, file_contents)
        file_object = self.pre_read(file_object)

        try:
            dataset = Dataset()

            try:
                self.format.import_set(dataset, file_object)
            except TypeError:
                # Versions of tablib>=0.11.5 expect a
                # buffer-like object to pass to BytesIO
                self.format.import_set(dataset, file_object.read())

            return dataset
        except (AttributeError, KeyError):
            raise InvalidFileError(_("Empty or Invalid File."))

    def export_set(self, dataset):
        return self.format.export_set(dataset)

    def write(self, dataset: Dataset) -> BytesIO:
        """Return a BytesIO stream representing a set of items."""
        data = self.export_set(dataset)
        return self._write_to_bytes(data)

    def _write_to_bytes(self, data) -> BytesIO:
        f = BytesIO()
        if isinstance(data, str):
            data = data.encode("utf-8")
        f.write(data)
        return f


class CsvFormat(TabLibFileFormat):
    def __init__(self):
        super(CsvFormat, self).__init__(
            _csv, "application/csv", read_file_as_string=True
        )

    @classmethod
    def ensure_unicode(cls, file_contents):
        if isinstance(file_contents, str):
            return file_contents
        charset = chardet.detect(file_contents)
        encoding = charset["encoding"]
        encoding_confidence = charset["confidence"]
        if encoding and encoding_confidence > 0.5:
            return file_contents.decode(encoding.lower()).encode("utf8")
        else:
            raise InvalidFileError(_("Unknown file type."))

    def pre_read(self, file_object):
        file_object = self.ensure_unicode(file_object)
        file_object = strings.normalize_string(file_object)
        return file_object

    def detect(self, file_handler, file_contents):
        if self.is_valid_csv(file_handler, file_contents):
            # Handles row validations
            return super(CsvFormat, self).detect(file_handler, file_contents)
        return False

    def is_valid_csv(self, file_handler, file_contents):
        file_object = self.get_file_object(file_handler, file_contents)
        try:
            # Would error out if invalid csv file
            Dataset().load(file_object, "csv")
            # Note: dataset is valid for test_file.yaml in the tests directory
            # Would need suggestions on how to better handle this
            return not YamlFormat().detect(file_handler, file_contents)
        except (InvalidDimensions, UnsupportedFormat, AttributeError, NullError):
            pass
        return False


class JsonFormat(TabLibFileFormat):
    def __init__(self):
        super(JsonFormat, self).__init__(
            _json,
            "application/json",
            read_file_as_string=True,
            empty_file_requires_example_row=True,
        )

    def export_set(self, dataset):
        return _json.json.dumps(
            dataset.dict,
            default=_json.date_handler,
            ensure_ascii=False,
            sort_keys=False,
            indent=2,
        )


class YamlFormat(TabLibFileFormat):
    def __init__(self):
        super(YamlFormat, self).__init__(
            _yaml, "application/x-yaml", empty_file_requires_example_row=True
        )

    def export_set(self, dataset):
        # By default use the C-based CSafeDumper,
        # otherwise fallback to pure Python SafeDumper.
        if CSafeDumper:
            return _yaml.yaml.dump(
                dataset._package(ordered=False),
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                Dumper=CSafeDumper,
            )
        else:
            return _yaml.yaml.safe_dump(
                dataset._package(ordered=False),
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

    def detect(self, file_handler, file_contents):
        try:
            return super(YamlFormat, self).detect(file_handler, file_contents)
        except _yaml.yaml.error.YAMLError:
            raise InvalidFileError(_("Invalid YAML File."))


class TxtFormat(FileFormat):
    title = "txt"
    content_type = "text/plain"

    def detect(self, file_handler, file_contents):
        return False

    def read(self, file_handler, file_contents):
        raise NotImplementedError()

    def write(self, dataset):
        f = BytesIO()
        stream = StringIO()

        for row in dataset._package():
            for key, val in row.items():
                stream.write("-" * len(key) + "\n")
                stream.write(key.encode("utf-8") + "\n")
                stream.write("-" * len(key) + "\n")
                stream.write(val.encode("utf-8") + "\n\n")
            stream.write("\n" + "*" * 50 + "\n\n\n")

        f.write(stream.getvalue())
        return f


csv = CsvFormat()

txt = TxtFormat()

xls = TabLibFileFormat(_xls, "application/vnd.ms-excel", read_file_as_string=True)

xlsx = TabLibFileFormat(
    _xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

json = JsonFormat()

yaml = YamlFormat()

all_formats = (xlsx, xls, csv, json, yaml, txt)

supported_mimetypes = (
    "text/plain",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/json",
    "application/x-yaml",
    "text/yaml",
    # When Content-Type unspecified, defaults to this.
    # https://sdelements.atlassian.net/browse/LIBR-355
    # https://stackoverflow.com/questions/12061030/why-am-i-getting-mime-type-of-csv-file-as-application-octet-stream
    "application/octet-stream",
)
