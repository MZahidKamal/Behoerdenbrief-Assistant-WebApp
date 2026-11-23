"""API tests: an `AppException` becomes a Problem Details response."""

from collections.abc import AsyncIterator

import allure
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import AppException
from app.main import create_app

# Allure groups the results by feature. Error handling belongs to no feature.
pytestmark = [allure.feature("server")]


class ExampleItemNotFoundError(AppException):
    """An invented error, only for these tests."""

    code = "not_found"
    status = 404
    title = "Resource not found"


@pytest.fixture
async def failing_route_client() -> AsyncIterator[AsyncClient]:
    """Give an HTTP client for the real app with two routes that always fail.

    Yields:
        A client that talks to the app in memory.
    """
    # The real app, so the real error handlers run.
    application = create_app()

    # One route raises the error without a detail, one with a detail.
    @application.get("/test/example-items/without-detail")
    async def get_example_item_without_detail() -> None:
        raise ExampleItemNotFoundError()

    @application.get("/test/example-items/with-detail")
    async def get_example_item_with_detail() -> None:
        raise ExampleItemNotFoundError("The example item does not exist.")

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
