"""Shared setup and fixtures for all backend tests."""

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

# Importing `app.main` builds the app, and that needs the required settings.
# pytest loads this file before any test module, so every test runs with
# these values, also on a computer or CI runner without a `.env` file.
# The address is invented; tests check error links against it.
TEST_FRONTEND_BASE_URL = "https://app.example.test"
os.environ["APP_ENV"] = "test"
os.environ["FRONTEND_BASE_URL"] = TEST_FRONTEND_BASE_URL
os.environ["CORS_ALLOWED_ORIGINS"] = TEST_FRONTEND_BASE_URL

from app.main import create_app  # noqa: E402  (APP_ENV must be set first)


@pytest.fixture
async def api_client() -> AsyncIterator[AsyncClient]:
    """Give an HTTP client that talks to a new app in memory.

    `ASGITransport` sends each request straight into the app. So no server
    and no network are needed, but the request still passes through all of
    FastAPI (routing, validation, responses).

    Yields:
        A client. Use paths like `/health`; the host name is not important.
    """
    async with AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
    ) as client:
        yield client
