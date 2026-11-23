"""Unit tests for the app errors and Problem Details in `app/core/exceptions.py`."""

import json

import allure
import pytest
from pydantic import HttpUrl

from app.core.exceptions import (
    PROBLEM_DETAILS_MEDIA_TYPE,
    AppException,
    CommonErrorCode,
    FieldErrorCode,
    ProblemDetailsResponse,
    build_json_pointer,
    build_problem_type_url,
    create_problem_details_response,
    get_error_code_for_http_status,
    get_field_error_code,
)

# Allure groups the results by feature. Error handling belongs to no feature.
pytestmark = [allure.feature("server")]


def _make_problem_details() -> ProblemDetailsResponse:
    # A complete body without `errors`, like every error except 422.
    return ProblemDetailsResponse(
        type="https://app.example.test/problems/method_not_allowed",
        title="Method Not Allowed",
        status=405,
        detail="Method Not Allowed",
        instance="/test",
        code="method_not_allowed",
    )


class ExampleItemNotFoundError(AppException):
    """An invented error, only for these tests."""

    code = "not_found"
    status = 404
    title = "Resource not found"


def test_common_error_code_has_all_documented_codes_when_enum_is_read() -> None:
    # Arrange: the table of API_DESIGN §3.3, copied by hand on purpose.
    documented_codes = {
        "malformed_request",
        "authentication_required",
        "invalid_token",
        "account_deleted",
        "profile_incomplete",
        "account_read_only",
        "forbidden",
        "mfa_required",
        "admin_session_expired",
        "not_found",
        "invalid_state",
        "request_too_large",
        "validation_failed",
        "rate_limited",
        "internal_error",
        "service_unavailable",
    }

    # Act
    enum_codes = {code.value for code in CommonErrorCode}

    # Assert: no code missing, no code too many.
    assert enum_codes == documented_codes


def test_build_problem_type_url_returns_problems_link_when_url_has_no_path() -> None:
    # Arrange: Pydantic adds a "/" at the end of a plain address.
    frontend_base_url = HttpUrl("https://app.example.test")

    # Act
    problem_type_url = build_problem_type_url(frontend_base_url, "not_found")

    # Assert: no "//" before `problems`.
    assert problem_type_url == "https://app.example.test/problems/not_found"


def test_build_problem_type_url_keeps_path_when_url_has_path() -> None:
    # Arrange
    frontend_base_url = HttpUrl("https://app.example.test/web/")

    # Act
    problem_type_url = build_problem_type_url(frontend_base_url, "not_found")

    # Assert
    assert problem_type_url == "https://app.example.test/web/problems/not_found"


def test_app_exception_uses_title_as_detail_when_detail_is_missing() -> None:
    # Arrange and act
    error = ExampleItemNotFoundError()

    # Assert
    assert error.detail == "Resource not found"


def test_app_exception_uses_given_detail_when_detail_is_given() -> None:
    # Arrange and act
    error = ExampleItemNotFoundError("The example item does not exist.")

    # Assert
    assert error.detail == "The example item does not exist."
    assert str(error) == "The example item does not exist."


def test_create_problem_details_response_sets_status_and_media_type_when_called() -> (
    None
):
    # Arrange
    problem_details = ProblemDetailsResponse(
        type="https://app.example.test/problems/not_found",
        title="Resource not found",
        status=404,
        detail="The example item does not exist.",
        instance="/api/v1/example-items/1",
        code="not_found",
    )

    # Act
    response = create_problem_details_response(problem_details)

    # Assert
    assert response.status_code == 404
    assert response.media_type == PROBLEM_DETAILS_MEDIA_TYPE
    assert json.loads(bytes(response.body)) == problem_details.model_dump(
        exclude_none=True
    )


def test_create_problem_details_response_leaves_out_errors_when_errors_missing() -> (
    None
):
    # Arrange
    problem_details = _make_problem_details()

    # Act
    response = create_problem_details_response(problem_details)

    # Assert
    assert "errors" not in json.loads(bytes(response.body))


def test_create_problem_details_response_adds_headers_when_headers_are_given() -> None:
    # Arrange
    problem_details = _make_problem_details()

    # Act
    response = create_problem_details_response(
        problem_details, headers={"Allow": "POST"}
    )

    # Assert
    assert response.headers["allow"] == "POST"


@pytest.mark.parametrize(
    ("location", "expected_pointer"),
    [
        (("body", "password"), "/password"),
        (("body", "items", 0), "/items/0"),
        (("body",), ""),
        (("query", "page"), "/query/page"),
        (("path", "letter_id"), "/path/letter_id"),
        (("body", "a/b", "c~d"), "/a~1b/c~0d"),
    ],
)
def test_build_json_pointer_returns_pointer_when_location_is_given(
    location: tuple[str | int, ...], expected_pointer: str
) -> None:
    # Arrange: the location comes from the parameters.

    # Act
    pointer = build_json_pointer(location)

    # Assert
    assert pointer == expected_pointer


@pytest.mark.parametrize(
    ("pydantic_error_type", "expected_code"),
    [
        ("missing", FieldErrorCode.REQUIRED),
        ("string_too_long", FieldErrorCode.TOO_LONG),
        ("too_short", FieldErrorCode.TOO_SHORT),
        ("greater_than_equal", FieldErrorCode.OUT_OF_RANGE),
        ("int_parsing", FieldErrorCode.INVALID_FORMAT),
        ("url_parsing", FieldErrorCode.INVALID_FORMAT),
        ("password_too_short", FieldErrorCode.PASSWORD_TOO_SHORT),
        ("consent_required", FieldErrorCode.CONSENT_REQUIRED),
    ],
)
def test_get_field_error_code_returns_our_code_when_pydantic_type_is_given(
    pydantic_error_type: str, expected_code: FieldErrorCode
) -> None:
    # Arrange: the type comes from the parameters.

    # Act
    code = get_field_error_code(pydantic_error_type)

    # Assert
    assert code == expected_code


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (400, "malformed_request"),
        (401, "authentication_required"),
        (404, "not_found"),
        (413, "request_too_large"),
        (429, "rate_limited"),
        (405, "method_not_allowed"),
        (415, "unsupported_media_type"),
        (499, "malformed_request"),
        (599, "internal_error"),
    ],
)
def test_get_error_code_for_http_status_returns_code_when_status_is_given(
    status_code: int, expected_code: str
) -> None:
    # Arrange: the status comes from the parameters.

    # Act
    code = get_error_code_for_http_status(status_code)

    # Assert
    assert code == expected_code
