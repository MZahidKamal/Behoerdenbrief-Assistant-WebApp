"""API tests: every answer has `Cache-Control: no-store` and the security headers."""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import allure
import httpx
import pytest
from fastapi import FastAPI, Response
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app

# Allure groups the results by feature. The headers belong to no feature.
pytestmark = [allure.feature("server")]

# The values of SECURITY §12 and MEMORY D-111, copied by hand on purpose.
# So a change in the code that nobody planned makes these tests fail.
EXPECTED_SECURITY_HEADERS = {
    "cache-control": "no-store",
    "strict-transport-security": "max-age=63072000; includeSubDomains",
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
}


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """Empty the settings cache before and after each test.

    Some tests build a "production" app. Without this, its settings could
    leak into the next test.

    Yields:
        Nothing. The test runs between the setup and the clean-up.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _add_test_routes(application: FastAPI) -> None:
    # A route that sets its own caching rule, which must be replaced.
    @application.get("/test/own-cache-control")
    async def get_own_cache_control_example() -> Response:
        return Response(content="{}", headers={"Cache-Control": "max-age=3600"})

    # A route with a checked query value, for a 422 answer.
    @application.get("/test/number")
    async def get_number_example(value: int) -> dict[str, int]:
        return {"value": value}

    # A route with a bug, for a 500 answer.
    @application.get("/test/unexpected-error")
    async def get_unexpected_error_example() -> None:
        raise RuntimeError("Example crash")


@asynccontextmanager
async def _open_api_client(
    monkeypatch: pytest.MonkeyPatch, app_env: str
) -> AsyncIterator[AsyncClient]:
    # Build a new app for this APP_ENV, with the test routes. After a crash
    # the client returns the 500 answer instead of raising, like a server.
    monkeypatch.setenv("APP_ENV", app_env)
    application = create_app()
    _add_test_routes(application)
    async with AsyncClient(
        transport=ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client


def _get_security_headers(response: httpx.Response) -> dict[str, str | None]:
    # Only the headers we check, with lowercase names.
    return {name: response.headers.get(name) for name in EXPECTED_SECURITY_HEADERS}


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/health", 200),
        ("/test/does-not-exist", 404),
        ("/test/number?value=abc", 422),
        ("/test/unexpected-error", 500),
    ],
)
async def test_answer_has_all_security_headers_when_path_is_called(
    monkeypatch: pytest.MonkeyPatch, path: str, expected_status: int
) -> None:
    # Arrange
    async with _open_api_client(monkeypatch, "test") as api_client:
        # Act
        response = await api_client.get(path)

    # Assert: normal answers and error answers, also the 500 answer that is
    # sent outside all middleware.
    assert response.status_code == expected_status
    assert _get_security_headers(response) == EXPECTED_SECURITY_HEADERS


async def test_answer_has_no_store_when_route_sets_own_cache_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    async with _open_api_client(monkeypatch, "test") as api_client:
        # Act
        response = await api_client.get("/test/own-cache-control")

    # Assert: our value replaces the route's value; there is only one.
    assert response.headers.get_list("cache-control") == ["no-store"]


@pytest.mark.parametrize("path", ["/docs", "/docs/oauth2-redirect"])
async def test_swagger_ui_has_no_content_security_policy_when_app_env_is_development(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    # Arrange
    async with _open_api_client(monkeypatch, "development") as api_client:
        # Act
        response = await api_client.get(path)

    # Assert: Swagger UI works, and all other headers are there.
    expected_headers = {
        name: value
        for name, value in EXPECTED_SECURITY_HEADERS.items()
        if name != "content-security-policy"
    }
    assert response.status_code == 200
    assert "content-security-policy" not in response.headers
    assert {name: response.headers.get(name) for name in expected_headers} == (
        expected_headers
    )


async def test_docs_path_has_all_security_headers_when_app_env_is_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    async with _open_api_client(monkeypatch, "production") as api_client:
        # Act
        response = await api_client.get("/docs")

    # Assert: in production `/docs` does not exist, so the strict rules apply.
    assert response.status_code == 404
    assert _get_security_headers(response) == EXPECTED_SECURITY_HEADERS
