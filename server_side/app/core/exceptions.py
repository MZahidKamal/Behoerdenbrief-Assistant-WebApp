"""Base class for app errors, and handlers that return Problem Details.

Every error response of the API has the same form: Problem Details
(RFC 9457, a web standard for error answers), with the media type
`application/problem+json` (API_DESIGN §3.1, MEMORY D-081).

Services never build error responses themselves. They raise a subclass of
`AppException`, and the handler here turns it into the response. Errors that
FastAPI creates by itself (validation errors, unknown routes, `HTTPException`)
get the same form.
"""

import re
from collections.abc import Mapping, Sequence
from enum import StrEnum
from http import HTTPStatus
from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import Settings

# RFC 9457 gives error answers their own media type. So the frontend can see
# at once that the body is an error and not normal data.
PROBLEM_DETAILS_MEDIA_TYPE = "application/problem+json"


class FieldErrorCode(StrEnum):
    """The codes of single field errors in the `errors` list (API_DESIGN §3.3)."""

    REQUIRED = "required"
    TOO_LONG = "too_long"
    TOO_SHORT = "too_short"
    INVALID_FORMAT = "invalid_format"
    OUT_OF_RANGE = "out_of_range"
    PASSWORD_TOO_SHORT = "password_too_short"  # noqa: S105  (an error code)
    CONSENT_REQUIRED = "consent_required"
    MINIMUM_AGE_NOT_MET = "minimum_age_not_met"


# Pydantic names its errors in its own way, for example `string_too_short`.
# The frontend only knows our field codes, so we translate the common ones.
# Every other Pydantic error becomes `invalid_format`.
_FIELD_ERROR_CODES_BY_PYDANTIC_TYPE: Mapping[str, FieldErrorCode] = {
    "missing": FieldErrorCode.REQUIRED,
    "string_too_long": FieldErrorCode.TOO_LONG,
    "bytes_too_long": FieldErrorCode.TOO_LONG,
    "too_long": FieldErrorCode.TOO_LONG,
    "string_too_short": FieldErrorCode.TOO_SHORT,
    "bytes_too_short": FieldErrorCode.TOO_SHORT,
    "too_short": FieldErrorCode.TOO_SHORT,
    "greater_than": FieldErrorCode.OUT_OF_RANGE,
    "greater_than_equal": FieldErrorCode.OUT_OF_RANGE,
    "less_than": FieldErrorCode.OUT_OF_RANGE,
    "less_than_equal": FieldErrorCode.OUT_OF_RANGE,
}

# These HTTP statuses have a fixed code in API_DESIGN §3.3. Every other status
# uses its HTTP name in snake_case, for example `405 method_not_allowed`.
_DOCUMENTED_ERROR_CODES_BY_STATUS: Mapping[int, str] = {
    400: "malformed_request",
    401: "authentication_required",
    404: "not_found",
    413: "request_too_large",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}


class AppException(Exception):
    """Base class for all expected errors of the app.

    Never raise `AppException` itself. Each feature defines subclasses in its
    `exceptions.py`, named `<Thing><Problem>Error` (RULES §2), and sets the three
    class values below. For example:

        class LetterNotFoundError(AppException):
            code = "not_found"
            status = 404
            title = "Resource not found"

    Attributes:
        code: The error code in snake_case. The frontend shows a translated
            text for it (API_DESIGN §3.3, §3.5).
        status: The HTTP status code of the response.
        title: A short English summary. It is the same every time this error
            happens.
        detail: An English text about this one case, for developers and logs.
            It must never contain personal data or letter content (RULES §7).

    Args:
        detail: Optional text about this one case. Without it, the response
            uses the title as `detail`, so the field is always there.
    """

    code: ClassVar[str]
    status: ClassVar[int]
    title: ClassVar[str]

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail if detail is not None else self.title
        super().__init__(self.detail)


class FieldErrorResponse(BaseModel):
    """One invalid field in a `422 validation_failed` response.

    Attributes:
        pointer: Where the field is, as a JSON pointer (RFC 6901). Body fields
            point into the JSON body (`/password`, `/items/0`); other parts of
            the request start with their name (`/query/page`).
        code: The field error code. The frontend translates by this value.
        detail: English text about the problem, never the input value.
    """

    pointer: str
    code: FieldErrorCode
    detail: str


class ProblemDetailsResponse(BaseModel):
    """The body of every error response (API_DESIGN §3.1).

    Attributes:
        type: A link that names the kind of problem:
            `<FRONTEND_BASE_URL>/problems/<code>`.
        title: Short English summary of this kind of problem.
        status: The HTTP status code, the same as the response status.
        detail: English text about this one case, never personal data.
        instance: The path of the request, for example `/api/v1/letters`.
        code: The error code. The frontend translates by this value.
        errors: Only for `422 validation_failed`: the invalid fields. Other
            responses leave this field out.
    """

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    errors: list[FieldErrorResponse] | None = None


def build_problem_type_url(frontend_base_url: HttpUrl, code: str) -> str:
    """Build the `type` link of a problem (API_DESIGN §3.1).

    Args:
        frontend_base_url: The address of the web app, from the settings.
        code: The error code, for example `not_found`.

    Returns:
        For example `https://example.app/problems/not_found`.
    """
    # Pydantic writes a plain address with a "/" at the end. We remove it,
    # so the link never has "//" in the middle.
    return f"{str(frontend_base_url).rstrip('/')}/problems/{code}"


def build_json_pointer(location: Sequence[str | int]) -> str:
    """Turn the place of a validation error into a JSON pointer (RFC 6901).

    FastAPI gives the place as a list: first the part of the request (`body`,
    `query`, `path`, `header`, `cookie`), then the field names and list
    positions.

    Args:
        location: For example `("body", "items", 0)` or `("query", "page")`.

    Returns:
        For example `/items/0` or `/query/page`. An error about the whole body
        gives `""`, which points to the whole document.
    """
    # Body fields point into the JSON body, as in API_DESIGN §3.1. Other parts
    # keep their name in front, so `?page=0` and a body field `page` differ.
    request_part, *field_path = location
    if request_part != "body":
        field_path = [request_part, *field_path]

    # RFC 6901 writes "~" as "~0" and "/" as "~1" inside a name, so a name
    # with these signs cannot break the pointer.
    return "".join(
        "/" + str(name).replace("~", "~0").replace("/", "~1") for name in field_path
    )


def get_field_error_code(pydantic_error_type: str) -> FieldErrorCode:
    """Find our field error code for one Pydantic error.

    Args:
        pydantic_error_type: The `type` of the Pydantic error, for example
            `string_too_short`, or one of our own codes from a validator.

    Returns:
        Our code, for example `too_short`. Unknown types give `invalid_format`.
    """
    # Our own validators raise errors that already have our code as type
    # (for example `password_too_short`), so these stay as they are.
    if pydantic_error_type in FieldErrorCode:
        return FieldErrorCode(pydantic_error_type)

    return _FIELD_ERROR_CODES_BY_PYDANTIC_TYPE.get(
        pydantic_error_type, FieldErrorCode.INVALID_FORMAT
    )


def get_error_code_for_http_status(status_code: int) -> str:
    """Find the error code for an `HTTPException` with this status.

    Args:
        status_code: The HTTP status, for example `404` or `405`.

    Returns:
        The code from API_DESIGN §3.3 (for example `not_found`), or else the
        HTTP name in snake_case (for example `method_not_allowed`).
    """
    # The statuses with a fixed code in API_DESIGN §3.3.
    if status_code in _DOCUMENTED_ERROR_CODES_BY_STATUS:
        return _DOCUMENTED_ERROR_CODES_BY_STATUS[status_code]

    # Python knows the name of every standard status. "Method Not Allowed"
    # becomes "method_not_allowed".
    try:
        status_name = HTTPStatus(status_code).phrase
    except ValueError:
        # A status that is not standard. Starlette cannot create one without
        # its own detail, so this is very rare.
        return "internal_error" if status_code >= 500 else "malformed_request"
    return re.sub(r"[^a-z0-9]+", "_", status_name.lower()).strip("_")


def _get_http_status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP error"


def create_problem_details_response(
    problem_details: ProblemDetailsResponse,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Turn the problem details into an HTTP response.

    Args:
        problem_details: The body of the error response.
        headers: Extra response headers, for example `Allow` after a wrong
            method.

    Returns:
        A response with the problem's status and the media type
        `application/problem+json`. Empty fields (like `errors` outside
        validation errors) are left out.
    """
    return JSONResponse(
        status_code=problem_details.status,
        content=problem_details.model_dump(mode="json", exclude_none=True),
        headers=headers,
        media_type=PROBLEM_DETAILS_MEDIA_TYPE,
    )


def register_exception_handlers(application: FastAPI, settings: Settings) -> None:
    """Connect the error handlers to the app.

    A later task adds the handler for unexpected errors (API_DESIGN §3.2).

    Args:
        application: The FastAPI app.
        settings: The app settings. `FRONTEND_BASE_URL` is used for the `type`
            link.
    """

    # All handlers build the body in the same way. The `instance` is only
    # the path, without the query string.
    def build_problem_details(
        request: Request,
        *,
        code: str,
        status: int,
        title: str,
        detail: str,
        errors: list[FieldErrorResponse] | None = None,
    ) -> ProblemDetailsResponse:
        return ProblemDetailsResponse(
            type=build_problem_type_url(settings.frontend_base_url, code),
            title=title,
            status=status,
            detail=detail,
            instance=request.url.path,
            code=code,
            errors=errors,
        )

    # An expected error from a service becomes a Problem Details response.
    @application.exception_handler(AppException)
    async def handle_app_exception(
        request: Request, error: AppException
    ) -> JSONResponse:
        problem_details = build_problem_details(
            request,
            code=error.code,
            status=error.status,
            title=error.title,
            detail=error.detail,
        )
        return create_problem_details_response(problem_details)

    # FastAPI checks every request with Pydantic. If the check fails, it
    # raises this error with one entry per problem.
    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        validation_errors = error.errors()

        # A body that is not JSON at all is a broken request, not a wrong
        # field: `400 malformed_request` (API_DESIGN §3.3).
        if any(
            validation_error["type"] == "json_invalid"
            for validation_error in validation_errors
        ):
            problem_details = build_problem_details(
                request,
                code="malformed_request",
                status=400,
                title="Malformed request",
                detail="The request body is not valid JSON.",
            )
            return create_problem_details_response(problem_details)

        # Wrong fields: one entry per field. We use Pydantic's English message,
        # but never its `input`, because the input can be personal data.
        field_errors = [
            FieldErrorResponse(
                pointer=build_json_pointer(validation_error["loc"]),
                code=get_field_error_code(validation_error["type"]),
                detail=validation_error["msg"],
            )
            for validation_error in validation_errors
        ]
        problem_details = build_problem_details(
            request,
            code="validation_failed",
            status=422,
            title="Request validation failed",
            detail="One or more fields are invalid.",
            errors=field_errors,
        )
        return create_problem_details_response(problem_details)

    # Starlette's `HTTPException` also covers FastAPI's `HTTPException`, and
    # the errors for unknown routes (404) and wrong methods (405).
    @application.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        title = _get_http_status_title(error.status_code)

        # Keep the error's own text if it is a text; else use the title.
        detail = error.detail if isinstance(error.detail, str) else title

        problem_details = build_problem_details(
            request,
            code=get_error_code_for_http_status(error.status_code),
            status=error.status_code,
            title=title,
            detail=detail,
        )

        # Keep the error's headers, for example `Allow: POST` after a wrong
        # method, or `WWW-Authenticate` after a missing login.
        return create_problem_details_response(problem_details, headers=error.headers)
