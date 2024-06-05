from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from rest_framework.settings import api_settings


def get_errors(exc):
    # ValidationError with just a string or list of strings
    # passed. Return as a non field error.
    if not hasattr(exc, "message_dict"):
        if hasattr(exc, "messages"):
            messages = exc.messages
        else:
            messages = [exc.message]
        return {api_settings.NON_FIELD_ERRORS_KEY: messages}

    errors = exc.message_dict

    # we convert django non field errors to DRF non field errors.
    if NON_FIELD_ERRORS in errors.keys():
        non_field_errors = []

        for error in errors.pop(NON_FIELD_ERRORS):
            # The error itself could be a ValidationError instead
            # of a string. If so, we use its message attribute.
            if isinstance(error, ValidationError):
                error = error.message

            non_field_errors.append(error)

        errors[api_settings.NON_FIELD_ERRORS_KEY] = non_field_errors

    return errors
