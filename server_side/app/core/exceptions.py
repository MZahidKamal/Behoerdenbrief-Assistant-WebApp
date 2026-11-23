"""Base class for app errors, and handlers that return Problem Details.

Every error response of the API has the same form: Problem Details
(RFC 9457, a web standard for error answers), with the media type
`application/problem+json` (API_DESIGN §3.1, MEMORY D-081).

Services never build error responses themselves. They raise a subclass of
`AppException`, and the handler here turns it into the response.
"""

from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from app.core.config import Settings

# RFC 9457 gives error answers their own media type. So the frontend can see
# at once that the body is an error and not normal data.
PROBLEM_DETAILS_MEDIA_TYPE = "application/problem+json"


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
    """

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str


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


def create_problem_details_response(
    problem_details: ProblemDetailsResponse,
) -> JSONResponse:
    """Turn the problem details into an HTTP response.

    Args:
        problem_details: The body of the error response.

    Returns:
        A response with the problem's status and the media type
        `application/problem+json`.
    """
    return JSONResponse(
        status_code=problem_details.status,
        content=problem_details.model_dump(),
        media_type=PROBLEM_DETAILS_MEDIA_TYPE,
    )


def register_exception_handlers(application: FastAPI, settings: Settings) -> None:
    """Connect the error handlers to the app.

    Later tasks add handlers here for validation errors, `HTTPException` and
    unexpected errors (API_DESIGN §3.2).

    Args:
        application: The FastAPI app.
        settings: The app settings. `FRONTEND_BASE_URL` is used for the `type`
            link.
    """

    # An expected error from a service becomes a Problem Details response.
    # The `instance` is only the path, without the query string.
    @application.exception_handler(AppException)
    async def handle_app_exception(
        request: Request, error: AppException
    ) -> JSONResponse:
        problem_details = ProblemDetailsResponse(
            type=build_problem_type_url(settings.frontend_base_url, error.code),
            title=error.title,
            status=error.status,
            detail=error.detail,
            instance=request.url.path,
            code=error.code,
        )
        return create_problem_details_response(problem_details)
