import zipfile
from io import BytesIO, StringIO

import chardet
import tablib
import tablib.formats._csv as csv
import tablib.formats._xls as xls
from django.http import HttpResponse
from tablib.core import Dataset

from multi_import.multi_importer import (InvalidDatasetError,
                                         MultiImportExporter,
                                         MultiImportResult)
from multi_import.utils import normalize_string


class InvalidFileError(Exception):
    pass


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
            file = StringIO()
            with zipfile.ZipFile(file, "w") as zf:
                for key, f in self.files.iteritems():
                    zf.writestr("{0}.{1}".format(key, self.file_format), f.getvalue())
            mimetype = "application-x-zip-compressed"
            filename = self.zip_filename + ".zip"

        response = HttpResponse(file.getvalue(), mimetype=mimetype)
        response['Content-Disposition'] = 'attachment; filename={0}'.format(filename)
        return response


class MultiFileImportExporter(MultiImportExporter):

    zip_filename = "export"
    file_formats = (xls, csv)

    def export_files(self, keys=None, template=False, file_format='csv'):
        datasets = self.export_datasets(keys, template)

        result = ExportResult(file_format, self.zip_filename)

        for key, dataset in datasets.datasets.iteritems():
            if file_format == 'xls':
                f = BytesIO()
                f.write(dataset.xls)
            else:
                f = StringIO()
                f.write(dataset.csv)
            result.add_result(key, f)

        return result

    def detect_tablib_format(self, stream):
        for fmt in self.file_formats:
            try:
                if fmt.detect(stream):
                    return fmt
            except AttributeError:
                pass
        return None

    def ensure_correct_file_type(self, file_contents):
        format = self.detect_tablib_format(file_contents)
        if not format:
            raise InvalidFileError('Invalid File Type.')
        return format

    def ensure_unicode(self, file_contents):
        charset = chardet.detect(file_contents)
        encoding, encoding_confidence = charset['encoding'], charset['confidence']
        if encoding and encoding_confidence > 0.5:
            return file_contents.decode(encoding.lower()).encode('utf8')
        else:
            raise InvalidFileError('Unknown file type.')

    def read_file(self, file):
        try:
            file.pos = 0
            file_contents = file.read()

            file_format = self.ensure_correct_file_type(file_contents)

            if not file_format:
                raise InvalidFileError('Invalid file format.')

            if file_format.title == 'csv':
                file_contents = self.ensure_unicode(file_contents)
                file_contents = normalize_string(file_contents)

            try:
                dataset = Dataset()
                file_format.import_set(dataset, file_contents)
                return dataset
            except AttributeError:
                pass

        except (tablib.InvalidDimensions, tablib.UnsupportedFormat):
            pass

        raise InvalidFileError('Empty or Invalid File.')

    def import_files(self, files):
        results = MultiImportResult()

        data = {}
        for filename, fp in files.iteritems():
            try:
                dataset_item = self.read_file(fp)
                data_item = self.identify_dataset(filename, dataset_item)
                data.update(data_item)
            except(InvalidDatasetError, InvalidFileError) as e:
                results.add_error(filename, e.message)

        if not results.valid:
            return results

        return self.import_datasets(data)
