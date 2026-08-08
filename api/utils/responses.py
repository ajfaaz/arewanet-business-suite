from rest_framework.response import Response
from rest_framework import status


def success(data=None, message="Success", status_code=status.HTTP_200_OK):
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def error(errors=None, message="Error", status_code=status.HTTP_400_BAD_REQUEST, code=None):
    payload = {
        "success": False,
        "message": message,
        "errors": errors or {},
    }
    if code:
        payload["code"] = code
    return Response(payload, status=status_code)
