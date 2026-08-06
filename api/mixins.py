from rest_framework.response import Response
from rest_framework import status


def api_response(data=None, message="Success", status_code=status.HTTP_200_OK, success=True, errors=None):
    payload = {
        "success": success,
        "message": message,
    }
    if data is not None:
        payload["data"] = data
    if errors is not None:
        payload["errors"] = errors
    return Response(payload, status=status_code)


class StandardResponseMixin:

    def success_response(self, data=None, message="Success", status_code=status.HTTP_200_OK):
        return api_response(data=data, message=message, status_code=status_code, success=True)

    def error_response(self, errors=None, message="An error occurred", status_code=status.HTTP_400_BAD_REQUEST):
        return api_response(errors=errors, message=message, status_code=status_code, success=False)
