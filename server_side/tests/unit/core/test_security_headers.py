"""Unit tests for the middleware in `app/core/security_headers.py`."""

import allure
from starlette.types import Message, Receive, Scope, Send

from app.core.security_headers import SecurityHeadersMiddleware

# Allure groups the results by feature. The headers belong to no feature.
pytestmark = [allure.feature("server")]


async def _receive_nothing() -> Message:
    return {"type": "lifespan.startup"}


async def test_security_headers_middleware_keeps_message_when_scope_is_not_http() -> (
    None
):
    # Arrange: an inner app that sends one start-up message.
    sent_messages: list[Message] = []

    async def inner_app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "lifespan.startup.complete"})

    async def remember_message(message: Message) -> None:
        sent_messages.append(message)

    middleware = SecurityHeadersMiddleware(inner_app, documentation_enabled=True)

    # Act
    await middleware({"type": "lifespan"}, _receive_nothing, remember_message)

    # Assert: the message is not changed and gets no headers.
    assert sent_messages == [{"type": "lifespan.startup.complete"}]
