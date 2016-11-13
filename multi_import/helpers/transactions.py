from django import db


class TransactionRollbackError(Exception):
    pass


def transaction(function):
    def wrapper(*args, **kwargs):
        commit = kwargs.pop('commit', True)
        trans = kwargs.pop('transaction', True)

        if not trans:
            return function(*args, **kwargs)

        result = None

        try:
            with db.transaction.atomic():
                result = function(*args, **kwargs)

                if not commit or not getattr(result, 'valid', True):
                    raise TransactionRollbackError()

        except TransactionRollbackError:
            pass

        return result

    return wrapper
