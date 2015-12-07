class ImportResult(object):
    """
    Results from an attempt to generate an import diff.
    Contains a list of errors, or if successful, a diff object.
    """
    def __init__(self, model_key, model):
        self.model = model
        self.errors = []
        self.results = []
        self.result = {
            'model': model_key,
            'results': self.results
        }

    @property
    def valid(self):
        return len(self.errors) == 0

    def add_errors(self, errors):
        self.errors.extend(errors)

    def add_row_error(self, row, message, column_name=None):
        error = {
            'line_number': row.line_number,
            'row_number': row.row_number,
            'message': message
        }
        if column_name:
            error['attribute'] = column_name
        self.errors.append(error)

    def add_row_errors(self, row, messages, column_name=None):
        for message in messages:
            self.add_row_error(row, message, column_name)

    def add_result(self, result, line_number, row_number):
        result['line_number'] = line_number
        result['row_number'] = row_number
        self.results.append(result)
