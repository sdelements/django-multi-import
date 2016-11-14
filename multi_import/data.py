import zipfile

from django.http import HttpResponse
from rest_framework.settings import api_settings
from tablib.compat import BytesIO


class RowStatus(object):
    unchanged = 1
    update = 2
    new = 3


class Row(object):
    """
    Represents a row in an imported Dataset
    """
    def __init__(self, row_number, line_number, data):
        self.row_number = row_number
        self.line_number = line_number
        self.data = data
        self.errors = None
        self.status = None
        self.diff = None

    def set_error(self, message):
        self.errors = {
            api_settings.NON_FIELD_ERRORS_KEY: [message]
        }

    def set_errors(self, errors):
        self.errors = errors

    def to_json(self):
        return {
            'row_number': self.row_number,
            'line_number': self.line_number,
            'data': self.data,
            'errors': self.errors,
            'status': self.status,
            'diff': self.diff,
        }

    @classmethod
    def from_json(cls, data):
        row = cls(
            row_number=data['row_number'],
            line_number=data['line_number'],
            data=data['data']
        )
        row.errors = data['errors']
        row.status = data['status']
        row.diff = data['diff']
        return row


class ImportResult(object):
    def __init__(self, key, headers=None, rows=None, error=None):
        self.key = key
        self.error = error
        self.headers = headers
        self.rows = rows or []

    @property
    def valid(self):
        return not self.error and not any(row.errors for row in self.rows)

    @property
    def errors(self):
        result = []
        for row in (row for row in self.rows if row.errors):
            for key, messages in row.errors.items():
                for message in messages:
                    error = {
                        'line_number': row.line_number,
                        'row_number': row.row_number,
                        'message': message
                    }
                    if key != api_settings.NON_FIELD_ERRORS_KEY:
                        error['attribute'] = key
                    result.append(error)
        return result

    @property
    def new_rows(self):
        return [row for row in self.rows if row.status == RowStatus.new]

    @property
    def updated_rows(self):
        return [row for row in self.rows if row.status == RowStatus.update]

    @property
    def unchanged_rows(self):
        return [row for row in self.rows if row.status == RowStatus.unchanged]

    @property
    def changes(self):
        return [row for row in self.rows if row.status != RowStatus.unchanged]

    def to_json(self):
        return {
            'key': self.key,
            'headers': self.headers,
            'rows': [row.to_json() for row in self.rows],
        }

    @classmethod
    def from_json(cls, data):
        return cls(
            key=data['key'],
            headers=data['headers'],
            rows=[Row.from_json(row) for row in data['rows']]
        )


class MultiImportResult(object):
    """
    Results from an attempt to generate an import diff for several files.
    """
    def __init__(self):
        self.files = []
        self.errors = {}

    @property
    def valid(self):
        return len(self.errors) == 0

    def add_result(self, filename, result):
        if result.valid is False:
            self.errors[filename] = result.errors

        self.files.append({
            'filename': filename,
            'result': result
        })

    def add_error(self, filename, message):
        self.errors[filename] = [{'message': message}]

    def num_changes(self):
        return sum(
            len(file['result'].changes) for file in self.files
        )

    def has_changes(self):
        return any(file['result'].changes for file in self.files)

    def to_json(self):
        return {
            'files': [
                {
                    'filename': file['filename'],
                    'result': file['result'].to_json(),
                }
                for file in self.files
            ]
        }

    @classmethod
    def from_json(cls, data):
        result = cls()
        for file in data['files']:
            result.add_result(file['filename'],
                              ImportResult.from_json(file['result']))
        return result


class MultiExportResult(object):
    """
    Results from an attempt to export multiple datasets.
    """
    def __init__(self):
        self.datasets = {}

    def add_result(self, key, dataset):
        self.datasets[key] = dataset


class MultiFileExportResult(object):
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
        if self.file_format == 'csv':
            return 'application/csv'
        elif self.file_format == 'txt':
            return 'text/plain'
        elif self.file_format == 'xls':
            return 'application/vnd.ms-excel'
        else:
            return (
                'application/'
                'vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

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
