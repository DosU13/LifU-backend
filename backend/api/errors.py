from rest_framework.views import exception_handler as drf_exception_handler

_CODE_BY_STATUS = {
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    429: "THROTTLED",
}


def exception_handler(exc, context):
    """Wrap DRF's own errors in the same envelope the views use.

    Validation errors (400) are left alone so per-field messages survive;
    views that already return an `error` envelope pass through untouched.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if response.status_code == 400:
        return response
    if isinstance(response.data, dict) and "error" in response.data:
        return response

    detail = None
    if isinstance(response.data, dict):
        detail = response.data.get("detail")
    response.data = {
        "error": {
            "code": _CODE_BY_STATUS.get(response.status_code, "ERROR"),
            "message": str(detail) if detail else "Request failed.",
        }
    }
    return response
