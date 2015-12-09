import zipfile

import chardet
import tablib
import tablib.formats._csv as csv
import tablib.formats._xls as xls
import tablib.formats._xlsx as xlsx
from django.http import HttpResponse
from tablib.core import Dataset
from tablib.compat import BytesIO

from multi_import.multi_importer import (InvalidDatasetError,
                                         MultiImportExporter,
                                         MultiImportResult)
from multi_import.utils import normalize_string


class InvalidFileError(Exception):
    pass


class FileFormat(object):
    def __init__(self, file_format, read_file_as_string=False):
        self.format = file_format
        self.read_file_as_string = read_file_as_string

    @property
    def key(self):
        return self.format.title

    def get_file_object(self, file_handler, file_contents):
        if self.read_file_as_string:
            return file_contents

        file_handler.pos = 0
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
        data = getattr(dataset, self.format.title)
        f = BytesIO()
        f.write(data)
        return f


class CsvFormat(FileFormat):
    def __init__(self):
        super(CsvFormat, self).__init__(csv, read_file_as_string=True)

    def ensure_unicode(self, file_contents):
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


class FileReadWriter(object):
    file_formats = (
        FileFormat(xlsx),
        FileFormat(xls, read_file_as_string=True),
        CsvFormat(),
    )

    def read(self, file_handler):
        file_handler.pos = 0
        file_contents = file_handler.read()

        for file_format in self.file_formats:
            try:
                if file_format.detect(file_handler, file_contents):
                    return file_format.read(file_handler, file_contents)
            except AttributeError:
                pass

        raise InvalidFileError('Invalid File Type.')

    def write(self, dataset, file_format=None):
        if file_format is None:
            writer = self.file_formats[0]
        else:
            writer = next(
                (f for f in self.file_formats if f.key == file_format),
                None)

        return writer.write(dataset)


class ExportResult(object):
    """
    Results from an attempt to export multiple files.
    """
    def __init__(self, file_format='csv', zip_filename='export'):
        self.file_format = file_format
        self.zip_filename = zip_filename
        self.files = {}

    def add_result(self, key, result):
        self.files[key] = result

    def get_mimetype(self):
        if self.file_format == 'xls':
            return "application/vnd.ms-excel"
        else:
            return "application/csv"

    def get_http_response(self):
        if len(self.files) == 1:
            key, file = self.files.items()[0]
            mimetype = self.get_mimetype()
            filename = "{0}.{1}".format(key, self.file_format)

        else:
            file = BytesIO()
            with zipfile.ZipFile(file, "w") as zf:
                for key, f in self.files.items():
                    fname = "{0}.{1}".format(key, self.file_format)
                    zf.writestr(fname, f.getvalue())
            mimetype = "application-x-zip-compressed"
            filename = self.zip_filename + ".zip"

        response = HttpResponse(file.getvalue(), mimetype=mimetype)
        header = 'attachment; filename={0}'.format(filename)
        response['Content-Disposition'] = header
        return response


class MultiFileImportExporter(MultiImportExporter):

    zip_filename = "export"

    def __init__(self, *args, **kwargs):
        super(MultiFileImportExporter, self).__init__(*args, **kwargs)
        self.file_writer = FileReadWriter()
        self.error_messages['invalid_file'] = u'Empty or Invalid File.'

    def export_files(self, keys=None, template=False, file_format='csv'):
        datasets = self.export_datasets(keys, template)

        result = ExportResult(file_format, self.zip_filename)

        for key, dataset in datasets.datasets.items():
            f = self.file_writer.write(dataset, file_format)
            result.add_result(key, f)

        return result

    def read_file(self, file_handler):
        try:
            return self.file_writer.read(file_handler)

        except (tablib.InvalidDimensions, tablib.UnsupportedFormat):
            raise InvalidFileError(self.error_messages['invalid_file'])

    def import_files(self, files, import_behaviour=None):
        results = MultiImportResult()

        data = {}
        for filename, fp in files.items():
            try:
                dataset = self.read_file(fp)
                model, data_item = self.identify_dataset(filename, dataset)
                if model in data:
                    data[model].append(data_item)
                else:
                    data[model] = [data_item]
            except(InvalidDatasetError, InvalidFileError) as e:
                results.add_error(filename, e.message)

        if not results.valid:
            return results

        return self.import_data(data, import_behaviour)

    def diff_generate_files(self, files):
        return self.import_files(files, self.import_diff_generator)
