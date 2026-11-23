"""API tests for the health check `GET /health`."""

import allure
from httpx import AsyncClient

# Allure groups the results by feature. The health check belongs to no feature.
pytestmark = [allure.feature("server")]


async def test_get_health_returns_200_with_only_status_ok_when_app_is_running(
    api_client: AsyncClient,
) -> None:
    # Arrange: the `api_client` fixture has built a new app.

    # Act
    response = await api_client.get("/health")

    # Assert: exactly this body, so no other data can leak (API_DESIGN §1.1).
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_get_health_returns_json_when_app_is_running(
    api_client: AsyncClient,
) -> None:
    # Arrange: the `api_client` fixture has built a new app.

    # Act
    response = await api_client.get("/health")

    # Assert
    assert response.headers["content-type"] == "application/json"
