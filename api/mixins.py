from rest_framework import status
from api.utils.responses import success as success_response_func, error as error_response_func, Response


def api_response(data=None, message="Success", status_code=status.HTTP_200_OK, success=True, errors=None):
    if success:
        return success_response_func(data=data, message=message, status_code=status_code)
    return error_response_func(errors=errors, message=message, status_code=status_code)


class StandardResponseMixin:

    def success_response(self, data=None, message="Success", status_code=status.HTTP_200_OK):
        return success_response_func(data=data, message=message, status_code=status_code)

    def error_response(self, errors=None, message="An error occurred", status_code=status.HTTP_400_BAD_REQUEST):
        return error_response_func(errors=errors, message=message, status_code=status_code)
