"""Stop requests whose body is larger than `MAX_UPLOAD_REQUEST_MB`.

A very large request could fill the server's memory and block it. So the
server stops reading at the limit and answers `413 request_too_large`
(API_DESIGN §1.8, §3.3, MEMORY D-113).

The check happens while the body is read: first with the `Content-Length`
header, then by counting the bytes, because a client can lie or send the body
without `Content-Length`. A route that never reads the body is not affected.
"""

from starlette.datastructures import Headers
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 1 MB = 1024 × 1024 bytes (MEMORY D-113).
BYTES_PER_MEGABYTE = 1024 * 1024


class RequestBodyTooLargeError(StarletteHTTPException):
    """The request body is larger than the limit.

    This error is an `HTTPException`, not an `AppException` (an exception to
    RULES §2, MEMORY D-113). It happens while FastAPI reads the body, and
    FastAPI turns every other error at that moment into a wrong
    `400 "There was an error parsing the body"`. Our `HTTPException` handler
    turns status 413 into Problem Details with the code `request_too_large`.

    Args:
        max_upload_request_mb: The limit in megabytes, for the `detail` text.
    """

    def __init__(self, max_upload_request_mb: int) -> None:
        super().__init__(
            status_code=413,
            detail=f"The request body is larger than {max_upload_request_mb} MB.",
        )


class RequestSizeLimitMiddleware:
    """Stop reading a request body as soon as it is larger than the limit.

    Args:
        app: The next part of the app that handles the request.
        max_upload_request_mb: The limit in megabytes, from the settings.
    """

    def __init__(self, app: ASGIApp, max_upload_request_mb: int) -> None:
        self.app = app
        self.max_upload_request_mb = max_upload_request_mb
        self.max_body_size_bytes = max_upload_request_mb * BYTES_PER_MEGABYTE

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Run one request and watch the size of its body.

        Args:
            scope: Information about the connection, for example its headers.
            receive: Reads the next part of the body from the client.
            send: Sends the next message to the client.

        Raises:
            RequestBodyTooLargeError: The body is larger than the limit. The
                error handler turns it into the `413` answer.
        """
        # Only HTTP requests have a body. WebSocket and lifespan pass through.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = _get_content_length(scope)
        received_bytes = 0

        # The app reads the body piece by piece through this function.
        async def receive_with_size_limit() -> Message:
            nonlocal received_bytes

            # The client says in advance that the body is too large: stop at
            # once, without reading anything.
            if content_length is not None and content_length > self.max_body_size_bytes:
                raise RequestBodyTooLargeError(self.max_upload_request_mb)

            # Count the real bytes, because `Content-Length` can be missing or
            # wrong. Stop as soon as the count is over the limit.
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_size_bytes:
                    raise RequestBodyTooLargeError(self.max_upload_request_mb)
            return message

        await self.app(scope, receive_with_size_limit, send)


def _get_content_length(scope: Scope) -> int | None:
    # A missing or broken header gives None; then only the counting works.
    content_length = Headers(scope=scope).get("content-length")
    if content_length is None:
        return None
    try:
        return int(content_length)
    except ValueError:
        return None
