"""Unit tests for the middleware in `app/core/request_size_limit.py`."""

import allure
import pytest
from starlette.types import Message, Receive, Scope, Send

from app.core.request_size_limit import (
    RequestBodyTooLargeError,
    RequestSizeLimitMiddleware,
)

# Allure groups the results by feature. The size limit belongs to no feature.
pytestmark = [allure.feature("server")]


def _make_receive(body: bytes) -> Receive:
    # A client that sends the whole body in one message.
    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


async def _send_nothing(message: Message) -> None:
    return None


async def _read_body(scope: Scope, receive: Receive, send: Send) -> None:
    # An inner app that reads one body message.
    await receive()


async def test_size_limit_middleware_passes_through_when_scope_is_lifespan() -> None:
    # Arrange: an inner app that remembers which scope it got.
    seen_scope_types: list[str] = []

    async def inner_app(scope: Scope, receive: Receive, send: Send) -> None:
        seen_scope_types.append(scope["type"])

    middleware = RequestSizeLimitMiddleware(inner_app, max_upload_request_mb=1)

    # Act
    await middleware({"type": "lifespan"}, _make_receive(b""), _send_nothing)

    # Assert
    assert seen_scope_types == ["lifespan"]


async def test_size_limit_middleware_stops_body_when_content_length_is_broken() -> None:
    # Arrange: a header that is not a number, and a body over the limit.
    scope: Scope = {"type": "http", "headers": [(b"content-length", b"abc")]}
    body = b"x" * (1024 * 1024 + 1)
    middleware = RequestSizeLimitMiddleware(_read_body, max_upload_request_mb=1)

    # Act and assert: the counting still stops the body.
    with pytest.raises(RequestBodyTooLargeError):
        await middleware(scope, _make_receive(body), _send_nothing)


async def test_size_limit_middleware_passes_message_when_client_disconnects() -> None:
    # Arrange: the client goes away instead of sending a body.
    received_messages: list[Message] = []

    async def receive_disconnect() -> Message:
        return {"type": "http.disconnect"}

    async def remember_message(scope: Scope, receive: Receive, send: Send) -> None:
        received_messages.append(await receive())

    middleware = RequestSizeLimitMiddleware(remember_message, max_upload_request_mb=1)

    # Act
    await middleware({"type": "http", "headers": []}, receive_disconnect, _send_nothing)

    # Assert: the app gets the message unchanged, and no bytes are counted.
    assert received_messages == [{"type": "http.disconnect"}]


async def test_size_limit_middleware_reads_body_when_content_length_is_broken() -> None:
    # Arrange: a broken header, and a small body.
    scope: Scope = {"type": "http", "headers": [(b"content-length", b"abc")]}
    middleware = RequestSizeLimitMiddleware(_read_body, max_upload_request_mb=1)

    # Act and assert: no error.
    await middleware(scope, _make_receive(b"small"), _send_nothing)
