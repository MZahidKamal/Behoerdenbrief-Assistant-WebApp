"""API tests: the API documentation exists only outside production."""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import allure
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app

# Allure groups the results by feature. The API documentation belongs to no feature.
pytestmark = [allure.feature("server")]


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """Empty the settings cache before and after each test.

    These tests build apps with different APP_ENV values. Without this, a
    "production" app could leak its settings into the next test.

    Yields:
        Nothing. The test runs between the setup and the clean-up.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@asynccontextmanager
async def _open_api_client(
    monkeypatch: pytest.MonkeyPatch, app_env: str
) -> AsyncIterator[AsyncClient]:
    # Build a new app for this APP_ENV and talk to it in memory.
    monkeypatch.setenv("APP_ENV", app_env)
    async with AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
async def test_get_api_documentation_returns_200_when_app_env_is_development(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    # Arrange
    async with _open_api_client(monkeypatch, "development") as api_client:
        # Act
        response = await api_client.get(path)

    # Assert
    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
async def test_get_api_documentation_returns_404_when_app_env_is_production(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    # Arrange
    async with _open_api_client(monkeypatch, "production") as api_client:
        # Act
        response = await api_client.get(path)

    # Assert: the page does not exist at all (SECURITY §12).
    assert response.status_code == 404


@pytest.mark.parametrize("app_env", ["development", "production"])
async def test_get_redoc_returns_404_when_app_env_is_any(
    monkeypatch: pytest.MonkeyPatch, app_env: str
) -> None:
    # Arrange
    async with _open_api_client(monkeypatch, app_env) as api_client:
        # Act
        response = await api_client.get("/redoc")

    # Assert
    assert response.status_code == 404


async def test_get_health_returns_200_when_app_env_is_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    async with _open_api_client(monkeypatch, "production") as api_client:
        # Act
        response = await api_client.get("/health")

    # Assert: Render still needs the health check in production.
    assert response.status_code == 200
