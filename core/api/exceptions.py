import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response

logger = logging.getLogger("arewanet_invoice")


def api_exception_handler(exc, context):
    """
    Central API exception handler returning predictable JSON responses for Flutter and web applications.
    """
    response = exception_handler(exc, context)

    if response is None:
        logger.error(f"[Unhandled Server Exception] {exc}", exc_info=True)
        return Response(
            {
                "success": False,
                "message": "An unexpected error occurred.",
                "code": "unexpected_error",
                "errors": {},
            },
            status=500,
        )

    data = response.data
    if hasattr(exc, "default_code"):
        code = str(exc.default_code)
    elif hasattr(exc, "code"):
        code = str(exc.code)
    elif response.status_code == 404:
        code = "not_found"
    elif response.status_code == 401:
        code = "not_authenticated"
    elif response.status_code == 403:
        code = "permission_denied"
    elif response.status_code == 400:
        code = "invalid"
    else:
        code = "error"

    if isinstance(data, dict) and "detail" in data:
        message = data["detail"]
        errors = {}
    elif isinstance(data, dict):
        message = "Validation failed."
        errors = data
    elif isinstance(data, list):
        message = "Validation failed."
        errors = {"non_field_errors": data}
    else:
        message = str(data)
        errors = {}

    return Response(
        {
            "success": False,
            "message": str(message),
            "code": str(code),
            "errors": errors,
        },
        status=response.status_code,
    )
