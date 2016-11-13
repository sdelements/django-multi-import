import zipfile

from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
import tablib
from tablib.compat import BytesIO

from multi_import.exceptions import InvalidFileError
from multi_import.formats import all_formats
from multi_import.helpers.transactions import transaction
from multi_import.multi_importer import (InvalidDatasetError,
                                         MultiImportExporter,
                                         MultiImportResult)


class FileReadWriter(object):
    file_formats = all_formats

    def read(self, file_handler):
        file_handler.seek(0)
        file_contents = file_handler.read()

        for file_format in self.file_formats:
            try:
                if file_format.detect(file_handler, file_contents):
                    return file_format.read(file_handler, file_contents)
            except AttributeError:
                pass

        raise InvalidFileError(_('Invalid File Type.'))

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

    def get_content_type(self):
        if self.file_format == 'xls':
            return "application/vnd.ms-excel"
        elif self.file_format == 'csv':
            return "application/csv"
        else:
            return "text/plain"

    def get_http_response(self):
        if len(self.files) == 1:
            key, file = self.files.items()[0]
            content_type = self.get_content_type()
            filename = "{0}.{1}".format(key, self.file_format)

        else:
            file = BytesIO()
            with zipfile.ZipFile(file, "w") as zf:
                for key, f in self.files.items():
                    fname = "{0}.{1}".format(key, self.file_format)
                    zf.writestr(fname, f.getvalue())
            content_type = "application-x-zip-compressed"
            filename = self.zip_filename + ".zip"

        response = HttpResponse(file.getvalue(), content_type=content_type)
        header = 'attachment; filename={0}'.format(filename)
        response['Content-Disposition'] = header
        return response


class MultiFileImportExporter(MultiImportExporter):

    zip_filename = "export"

    def __init__(self, *args, **kwargs):
        super(MultiFileImportExporter, self).__init__(*args, **kwargs)
        self.file_writer = FileReadWriter()
        self.error_messages['invalid_file'] = _(u'Empty or Invalid File.')

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

    @transaction
    def import_files(self, files):
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

        return self.import_data(data, transaction=False)
