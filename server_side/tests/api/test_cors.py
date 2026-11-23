"""API tests: only the allowed origins may read API answers in a browser.

A browser sends its page's address in the `Origin` header. The API answers
with `Access-Control-Allow-Origin` only for allowed origins (SECURITY §12,
MEMORY D-112). `CORS_ALLOWED_ORIGINS` is set in `tests/conftest.py`.
"""

from collections.abc import AsyncIterator

import allure
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

# Allure groups the results by feature. CORS belongs to no feature.
pytestmark = [allure.feature("server")]

# The allowed origin from `tests/conftest.py`, and an invented other website.
ALLOWED_ORIGIN = "https://app.example.test"
OTHER_ORIGIN = "https://other-website.example.test"


@pytest.fixture
async def cors_client() -> AsyncIterator[AsyncClient]:
    """Give an HTTP client for the real app with one route that crashes.

    Yields:
        A client that talks to the app in memory. After a crash it returns the
        500 answer instead of raising, like a real server.
    """
    application = create_app()

    @application.get("/test/unexpected-error")
    async def get_unexpected_error_example() -> None:
        raise RuntimeError("Example crash")

    async with AsyncClient(
        transport=ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client


def _preflight_headers(
    origin: str, method: str = "POST", headers: str = "Authorization, Content-Type"
) -> dict[str, str]:
    # The headers a browser sends in its `OPTIONS` question before the request.
    return {
        "Origin": origin,
        "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": headers,
    }


async def test_request_gets_allow_origin_when_origin_is_allowed(
    cors_client: AsyncClient,
) -> None:
    # Arrange
    headers = {"Origin": ALLOWED_ORIGIN}

    # Act
    response = await cors_client.get("/health", headers=headers)

    # Assert: exactly this origin, never `*`, and no cookies.
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "access-control-allow-credentials" not in response.headers
    assert response.headers["access-control-expose-headers"] == "Retry-After"


async def test_request_gets_no_allow_origin_when_origin_is_other_website(
    cors_client: AsyncClient,
) -> None:
    # Arrange
    headers = {"Origin": OTHER_ORIGIN}

    # Act
    response = await cors_client.get("/health", headers=headers)

    # Assert: the API still answers (CORS is a browser rule), but without
    # permission the browser hides the answer from the other website.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


async def test_preflight_returns_200_with_rules_when_origin_is_allowed(
    cors_client: AsyncClient,
) -> None:
    # Arrange
    headers = _preflight_headers(ALLOWED_ORIGIN, method="PATCH")

    # Act
    response = await cors_client.options("/health", headers=headers)

    # Assert: the browser may send PATCH with these headers.
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-methods"] == (
        "GET, POST, PATCH, DELETE"
    )
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers


async def test_preflight_has_security_headers_when_origin_is_allowed(
    cors_client: AsyncClient,
) -> None:
    # Arrange
    headers = _preflight_headers(ALLOWED_ORIGIN)

    # Act
    response = await cors_client.options("/health", headers=headers)

    # Assert: CORS runs inside the security headers middleware.
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "preflight_headers",
    [
        _preflight_headers(OTHER_ORIGIN),
        _preflight_headers(ALLOWED_ORIGIN, method="PUT"),
        _preflight_headers(ALLOWED_ORIGIN, headers="X-Unknown-Header"),
    ],
    ids=["other_origin", "unknown_method", "unknown_header"],
)
async def test_preflight_returns_400_without_permission_when_request_is_not_allowed(
    cors_client: AsyncClient, preflight_headers: dict[str, str]
) -> None:
    # Arrange: the headers come from the parameters.

    # Act
    response = await cors_client.options("/health", headers=preflight_headers)

    # Assert: the browser will not send the real request.
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") != OTHER_ORIGIN


async def test_unexpected_error_gets_allow_origin_when_origin_is_allowed(
    cors_client: AsyncClient,
) -> None:
    # Arrange
    headers = {"Origin": ALLOWED_ORIGIN}

    # Act
    response = await cors_client.get("/test/unexpected-error", headers=headers)

    # Assert: the 500 answer is sent outside all middleware, so its handler
    # adds the permission itself. The frontend can read `internal_error`.
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["vary"] == "Origin"
    assert response.json()["code"] == "internal_error"


async def test_unexpected_error_gets_no_allow_origin_when_origin_is_other_website(
    cors_client: AsyncClient,
) -> None:
    # Arrange
    headers = {"Origin": OTHER_ORIGIN}

    # Act
    response = await cors_client.get("/test/unexpected-error", headers=headers)

    # Assert
    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers
