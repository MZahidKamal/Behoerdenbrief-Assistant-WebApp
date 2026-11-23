"""Unit tests for the app errors and Problem Details in `app/core/exceptions.py`."""

import json

import allure
from pydantic import HttpUrl

from app.core.exceptions import (
    PROBLEM_DETAILS_MEDIA_TYPE,
    AppException,
    ProblemDetailsResponse,
    build_problem_type_url,
    create_problem_details_response,
)

# Allure groups the results by feature. Error handling belongs to no feature.
pytestmark = [allure.feature("server")]


class ExampleItemNotFoundError(AppException):
    """An invented error, only for these tests."""

    code = "not_found"
    status = 404
    title = "Resource not found"


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
    assert json.loads(bytes(response.body)) == problem_details.model_dump()
