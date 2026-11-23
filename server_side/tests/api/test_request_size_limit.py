"""API tests: request bodies larger than `MAX_UPLOAD_REQUEST_MB` get `413`.

The tests use a limit of 1 MB instead of 30 MB, so they stay fast.
"""

from collections.abc import AsyncIterator, Iterator

import allure
import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.config import get_settings
from app.main import create_app

# Allure groups the results by feature. The size limit belongs to no feature.
pytestmark = [allure.feature("server")]

ONE_MEGABYTE = 1024 * 1024


class ExampleTextRequest(BaseModel):
    """An invented JSON body, only for these tests.

    Attributes:
        text: Any text.
    """

    text: str


@pytest.fixture
async def size_limit_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    """Give an HTTP client for the real app with a limit of 1 MB.

    Args:
        monkeypatch: Sets `MAX_UPLOAD_REQUEST_MB` only for one test.

    Yields:
        A client that talks to the app in memory.
    """
    # Build the app with a small limit. The settings cache is emptied, so the
    # app reads the new value.
    monkeypatch.setenv("MAX_UPLOAD_REQUEST_MB", "1")
    get_settings.cache_clear()
    application = create_app()

    # A route that reads the raw body and returns its size.
    @application.post("/test/body-size")
    async def get_body_size_example(request: Request) -> dict[str, int]:
        return {"size": len(await request.body())}

    # A route with a JSON body that FastAPI reads and checks.
    @application.post("/test/json-text")
    async def get_json_text_example(example_text: ExampleTextRequest) -> None:
        return None

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """Empty the settings cache after each test.

    So the small limit of these tests never reaches another test.

    Yields:
        Nothing. The test runs before the clean-up.
    """
    yield
    get_settings.cache_clear()


async def _make_chunks(total_size: int) -> AsyncIterator[bytes]:
    # Send the body in pieces of 64 KB. httpx then sends no `Content-Length`.
    chunk_size = 64 * 1024
    for start in range(0, total_size, chunk_size):
        yield b"x" * min(chunk_size, total_size - start)


async def test_large_body_returns_413_request_too_large_when_content_length_is_too_big(
    size_limit_client: AsyncClient,
) -> None:
    # Arrange: one byte more than the limit.
    body = b"x" * (ONE_MEGABYTE + 1)

    # Act
    response = await size_limit_client.post("/test/body-size", content=body)

    # Assert: Problem Details with the documented code (API_DESIGN §3.3).
    assert response.status_code == 413
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "https://app.example.test/problems/request_too_large",
        "title": "Content Too Large",
        "status": 413,
        "detail": "The request body is larger than 1 MB.",
        "instance": "/test/body-size",
        "code": "request_too_large",
    }


async def test_large_body_returns_413_when_body_has_no_content_length(
    size_limit_client: AsyncClient,
) -> None:
    # Arrange: a body in pieces, without `Content-Length`.
    chunks = _make_chunks(ONE_MEGABYTE + 1)

    # Act
    response = await size_limit_client.post("/test/body-size", content=chunks)

    # Assert: the counting finds it.
    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"


async def test_large_json_body_returns_413_not_400_when_fastapi_reads_body(
    size_limit_client: AsyncClient,
) -> None:
    # Arrange: a JSON body that is too large.
    body = {"text": "x" * (ONE_MEGABYTE + 1)}

    # Act
    response = await size_limit_client.post("/test/json-text", json=body)

    # Assert: FastAPI does not turn the error into "400 error parsing the body".
    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"


async def test_large_body_answer_has_security_headers_when_body_is_too_big(
    size_limit_client: AsyncClient,
) -> None:
    # Arrange
    body = b"x" * (ONE_MEGABYTE + 1)

    # Act
    response = await size_limit_client.post("/test/body-size", content=body)

    # Assert: the 413 answer passes through our middleware (SECURITY §12).
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("use_chunks", [False, True], ids=["content_length", "chunks"])
async def test_body_returns_200_when_body_is_exactly_at_limit(
    size_limit_client: AsyncClient, use_chunks: bool
) -> None:
    # Arrange: exactly 1 MB is still allowed.
    content: bytes | AsyncIterator[bytes] = (
        _make_chunks(ONE_MEGABYTE) if use_chunks else b"x" * ONE_MEGABYTE
    )

    # Act
    response = await size_limit_client.post("/test/body-size", content=content)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"size": ONE_MEGABYTE}
