import chardet
from tablib.formats import _csv, _xls, _xlsx
from tablib.core import Dataset
from tablib.compat import BytesIO, StringIO

from multi_import.exceptions import InvalidFileError
from multi_import.utils import normalize_string


class FileFormat(object):
    title = None

    @property
    def key(self):
        return self.title

    def detect(self, file_handler, file_contents):
        return False

    def pre_read(self, file_object):
        return file_object

    def read(self, file_handler, file_contents):
        raise NotImplementedError()

    def write(self, dataset):
        raise NotImplementedError()


class TabLibFileFormat(FileFormat):
    def __init__(self, file_format, read_file_as_string=False):
        self.format = file_format
        self.read_file_as_string = read_file_as_string

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
            return self.format.detect(file_object)
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
            self.format.import_set(dataset, self.pre_read(file_object))
            return dataset
        except AttributeError:
            raise InvalidFileError('Empty or Invalid File.')

    def write(self, dataset):
        data = self.format.export_set(dataset)
        f = BytesIO()
        f.write(data)
        return f


class CsvFormat(TabLibFileFormat):
    def __init__(self):
        super(CsvFormat, self).__init__(_csv, read_file_as_string=True)

    @classmethod
    def ensure_unicode(cls, file_contents):
        charset = chardet.detect(file_contents)
        encoding = charset['encoding']
        encoding_confidence = charset['confidence']
        if encoding and encoding_confidence > 0.5:
            return file_contents.decode(encoding.lower()).encode('utf8')
        else:
            raise InvalidFileError('Unknown file type.')

    def pre_read(self, file_object):
        file_object = self.ensure_unicode(file_object)
        file_object = normalize_string(file_object)
        return file_object


class TxtFormat(FileFormat):
    title = 'txt'

    def detect(self, file_handler, file_contents):
        return False

    def read(self, file_handler, file_contents):
        raise NotImplementedError()

    def write(self, dataset):
        f = BytesIO()
        stream = StringIO()

        for row in dataset._package():
            for key, val in row.items():
                stream.write('-' * len(key) + '\n')
                stream.write(key.encode('utf-8') + '\n')
                stream.write('-' * len(key) + '\n')
                stream.write(val.encode('utf-8') + '\n\n')
            stream.write('\n' + '*' * 50 + '\n\n\n')

        f.write(stream.getvalue())
        return f


csv = CsvFormat()
txt = TxtFormat()
xls = TabLibFileFormat(_xls, read_file_as_string=True)
xlsx = TabLibFileFormat(_xlsx)

all_formats = (
    xlsx,
    xls,
    csv,
    txt,
)
