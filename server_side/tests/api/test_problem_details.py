"""API tests: every error becomes a Problem Details response.

Covered: `AppException`, validation errors, broken JSON, unknown routes, wrong
methods and `HTTPException` (API_DESIGN §3.1, §3.3).
"""

from collections.abc import AsyncIterator

import allure
import pytest
from fastapi import HTTPException, Query
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.core.exceptions import AppException
from app.main import create_app

# Allure groups the results by feature. Error handling belongs to no feature.
pytestmark = [allure.feature("server")]

# An invented value. Tests check that the input never comes back in an error.
EXAMPLE_PERSONAL_VALUE = "invented-personal-value"


class ExampleItemNotFoundError(AppException):
    """An invented error, only for these tests."""

    code = "not_found"
    status = 404
    title = "Resource not found"


class ExampleItemCreateRequest(BaseModel):
    """An invented request body, only for these tests.

    Attributes:
        name: At least 2 characters.
        amounts: A list of whole numbers.
    """

    name: str = Field(min_length=2)
    amounts: list[int]


@pytest.fixture
async def failing_route_client() -> AsyncIterator[AsyncClient]:
    """Give an HTTP client for the real app with extra test routes.

    Yields:
        A client that talks to the app in memory.
    """
    # The real app, so the real error handlers run.
    application = create_app()

    # Two routes raise our own error: without and with a detail.
    @application.get("/test/example-items/without-detail")
    async def get_example_item_without_detail() -> None:
        raise ExampleItemNotFoundError()

    @application.get("/test/example-items/with-detail")
    async def get_example_item_with_detail() -> None:
        raise ExampleItemNotFoundError("The example item does not exist.")

    # A route with a checked body and a checked query value. A GET to the
    # same path is a wrong method (405).
    @application.post("/test/example-items")
    async def create_example_item(
        example_item: ExampleItemCreateRequest, page: int = Query(ge=1)
    ) -> None:
        return None

    # Two routes raise FastAPI's `HTTPException`: one with a standard status,
    # one with a status that Python does not know.
    @application.get("/test/forbidden")
    async def get_forbidden_example() -> None:
        raise HTTPException(status_code=403, detail="Example forbidden.")

    @application.get("/test/non-standard-status")
    async def get_non_standard_status_example() -> None:
        raise HTTPException(status_code=599, detail="Example non-standard status.")

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        yield client


async def test_app_exception_returns_problem_details_when_route_raises_it(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: the fixture has built the app with the failing routes.

    # Act
    response = await failing_route_client.get(
        "/test/example-items/with-detail", params={"page": "2"}
    )

    # Assert: exactly these fields (API_DESIGN §3.1). The address comes from
    # FRONTEND_BASE_URL in `tests/conftest.py`. `instance` has no query string.
    assert response.status_code == 404
    assert response.json() == {
        "type": "https://app.example.test/problems/not_found",
        "title": "Resource not found",
        "status": 404,
        "detail": "The example item does not exist.",
        "instance": "/test/example-items/with-detail",
        "code": "not_found",
    }


async def test_app_exception_returns_problem_json_media_type_when_route_raises_it(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: the fixture has built the app with the failing routes.

    # Act
    response = await failing_route_client.get("/test/example-items/with-detail")

    # Assert
    assert response.headers["content-type"] == "application/problem+json"


async def test_app_exception_returns_title_as_detail_when_detail_is_missing(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: the fixture has built the app with the failing routes.

    # Act
    response = await failing_route_client.get("/test/example-items/without-detail")

    # Assert
    assert response.json()["detail"] == "Resource not found"


async def test_invalid_fields_return_422_validation_failed_when_body_and_query_wrong(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: page too small, name too short, an amount that is no number.
    body = {"name": "a", "amounts": [EXAMPLE_PERSONAL_VALUE]}

    # Act
    response = await failing_route_client.post(
        "/test/example-items", params={"page": "0"}, json=body
    )

    # Assert: the main fields (API_DESIGN §3.1).
    problem = response.json()
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert problem["type"] == "https://app.example.test/problems/validation_failed"
    assert problem["title"] == "Request validation failed"
    assert problem["status"] == 422
    assert problem["detail"] == "One or more fields are invalid."
    assert problem["instance"] == "/test/example-items"
    assert problem["code"] == "validation_failed"

    # Assert: one entry per field. Body fields point into the body, the
    # query value starts with `/query`. Pydantic's names are translated.
    assert [(error["pointer"], error["code"]) for error in problem["errors"]] == [
        ("/query/page", "out_of_range"),
        ("/name", "too_short"),
        ("/amounts/0", "invalid_format"),
    ]
    assert all(error["detail"] for error in problem["errors"])


async def test_invalid_fields_never_return_input_when_input_is_wrong(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: the wrong value stands for personal data.
    body = {"name": "valid name", "amounts": [EXAMPLE_PERSONAL_VALUE]}

    # Act
    response = await failing_route_client.post(
        "/test/example-items", params={"page": "1"}, json=body
    )

    # Assert
    assert response.status_code == 422
    assert EXAMPLE_PERSONAL_VALUE not in response.text


async def test_missing_body_returns_required_error_for_whole_body_when_body_is_empty(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: no body at all.

    # Act
    response = await failing_route_client.post(
        "/test/example-items", params={"page": "1"}
    )

    # Assert: the pointer "" means the whole body.
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"pointer": "", "code": "required", "detail": "Field required"}
    ]


async def test_broken_json_returns_400_malformed_request_when_body_is_not_json(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: a body that is not valid JSON.
    headers = {"content-type": "application/json"}

    # Act
    response = await failing_route_client.post(
        "/test/example-items", params={"page": "1"}, content="{broken", headers=headers
    )

    # Assert: a broken request, so no `errors` list (API_DESIGN §3.3).
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "https://app.example.test/problems/malformed_request",
        "title": "Malformed request",
        "status": 400,
        "detail": "The request body is not valid JSON.",
        "instance": "/test/example-items",
        "code": "malformed_request",
    }


async def test_unknown_route_returns_404_not_found_when_path_does_not_exist(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: no route has this path.

    # Act
    response = await failing_route_client.get("/test/does-not-exist")

    # Assert
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "https://app.example.test/problems/not_found",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
        "instance": "/test/does-not-exist",
        "code": "not_found",
    }


async def test_wrong_method_returns_405_with_allow_header_when_method_is_not_allowed(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: the path exists only for POST.

    # Act
    response = await failing_route_client.get("/test/example-items")

    # Assert: the status name becomes the code, and the header stays.
    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    assert response.json()["code"] == "method_not_allowed"
    assert response.json()["title"] == "Method Not Allowed"


async def test_http_exception_returns_problem_details_when_route_raises_it(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: the route raises `HTTPException(403, "Example forbidden.")`.

    # Act
    response = await failing_route_client.get("/test/forbidden")

    # Assert
    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "https://app.example.test/problems/forbidden",
        "title": "Forbidden",
        "status": 403,
        "detail": "Example forbidden.",
        "instance": "/test/forbidden",
        "code": "forbidden",
    }


async def test_http_exception_returns_general_title_when_status_is_not_standard(
    failing_route_client: AsyncClient,
) -> None:
    # Arrange: the route raises `HTTPException(599, ...)`.

    # Act
    response = await failing_route_client.get("/test/non-standard-status")

    # Assert
    assert response.status_code == 599
    assert response.json()["title"] == "HTTP error"
    assert response.json()["code"] == "internal_error"
    assert response.json()["detail"] == "Example non-standard status."
