"""API tests for the request id that the middleware gives every request."""

import io
import logging
import re
from collections.abc import AsyncIterator

import allure
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.logging import APP_LOG_HANDLER_NAME, current_request_id
from app.main import create_app

# Allure groups the results by feature. The request id belongs to no feature.
pytestmark = [allure.feature("server")]

# A new request id is a UUID in hex form: 32 characters 0-9 and a-f.
REQUEST_ID_PATTERN = re.compile(r"[0-9a-f]{32}")


def _create_app_with_logging_route() -> FastAPI:
    # The real app, plus one test route that writes a log line and returns
    # the request id that it sees.
    application = create_app()

    @application.get("/test/request-id")
    async def get_request_id_for_test() -> dict[str, str | None]:
        logging.getLogger("app.test").info("Test route called")
        return {"request_id": current_request_id.get()}

    return application


@pytest.fixture
def log_output() -> io.StringIO:
    """Give an empty text buffer that collects the app's log lines.

    Returns:
        The buffer. The `logging_route_client` fixture connects it.
    """
    return io.StringIO()


@pytest.fixture
async def logging_route_client(
    log_output: io.StringIO,
) -> AsyncIterator[AsyncClient]:
    """Give an HTTP client for an app with the extra test route.

    The app's own log handler (with its filters) writes into `log_output`
    instead of standard output, so the test can read the lines.

    Args:
        log_output: The buffer for the log lines.

    Yields:
        A client that talks to the app in memory.
    """
    # Build the app first: it sets up a new app log handler.
    application = _create_app_with_logging_route()

    # Send the lines of this handler into the buffer.
    for handler in logging.getLogger().handlers:
        if handler.get_name() == APP_LOG_HANDLER_NAME and isinstance(
            handler, logging.StreamHandler
        ):
            handler.setStream(log_output)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        yield client


async def test_request_returns_new_request_id_when_route_runs(
    logging_route_client: AsyncClient,
) -> None:
    # Arrange: the fixture has built the app.

    # Act
    response = await logging_route_client.get("/test/request-id")

    # Assert
    assert REQUEST_ID_PATTERN.fullmatch(response.json()["request_id"])


async def test_request_ignores_client_request_id_when_header_is_sent(
    logging_route_client: AsyncClient,
) -> None:
    # Arrange: a client tries to choose its own id.
    headers = {"X-Request-ID": "fake-id-from-client"}

    # Act
    response = await logging_route_client.get("/test/request-id", headers=headers)

    # Assert: we always make our own id.
    assert response.json()["request_id"] != "fake-id-from-client"
    assert REQUEST_ID_PATTERN.fullmatch(response.json()["request_id"])


async def test_requests_get_different_request_ids_when_sent_one_after_another(
    logging_route_client: AsyncClient,
) -> None:
    # Arrange: the fixture has built the app.

    # Act
    first_response = await logging_route_client.get("/test/request-id")
    second_response = await logging_route_client.get("/test/request-id")

    # Assert
    assert first_response.json()["request_id"] != second_response.json()["request_id"]


async def test_request_removes_request_id_when_request_has_ended(
    logging_route_client: AsyncClient,
) -> None:
    # Arrange: the fixture has built the app.

    # Act
    await logging_route_client.get("/test/request-id")

    # Assert: the test runs outside a request, so it sees no id.
    assert current_request_id.get() is None


async def test_log_line_contains_request_id_when_written_during_request(
    logging_route_client: AsyncClient,
    log_output: io.StringIO,
) -> None:
    # Arrange: the fixture has built the app.

    # Act
    response = await logging_route_client.get("/test/request-id")

    # Assert: the line of the test route has the same id as the response.
    request_id = response.json()["request_id"]
    log_lines = log_output.getvalue().splitlines()
    route_lines = [line for line in log_lines if "Test route called" in line]
    assert len(route_lines) == 1
    assert route_lines[0].endswith(f"request_id={request_id}")
