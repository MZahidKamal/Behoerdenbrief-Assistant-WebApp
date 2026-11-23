"""Add `Cache-Control: no-store` and the security headers to every API answer.

The headers tell the browser how to treat our answers safely (SECURITY §12,
API_DESIGN §1.3, MEMORY D-111). The middleware adds them to every answer.
Only the `500` answer is sent outside all middleware, so its handler in
`core/exceptions.py` adds the same headers itself.
"""

from collections.abc import Mapping

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# The header with the content rules. Swagger UI cannot work with it.
CONTENT_SECURITY_POLICY_HEADER = "Content-Security-Policy"

SECURITY_HEADERS: Mapping[str, str] = {
    # Our answers hold personal data, so no browser, proxy or service worker
    # may keep a copy (SECURITY §12, API_DESIGN §1.3).
    "Cache-Control": "no-store",
    # Use only HTTPS for this site and its subdomains for 2 years. Browsers
    # ignore this header over plain `http://localhost`.
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    # A JSON answer may load nothing and may never be shown inside a frame.
    CONTENT_SECURITY_POLICY_HEADER: "default-src 'none'; frame-ancestors 'none'",
    # Trust our `Content-Type`; do not guess another type from the content.
    "X-Content-Type-Options": "nosniff",
    # Send other sites only our address, never the full path.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # The API never needs the camera, the microphone or the location.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# Swagger UI loads scripts from a CDN and has an inline script, so the strict
# content rules would break it. These pages exist only outside production
# (SECURITY §12, MEMORY D-109).
SWAGGER_UI_PATHS = frozenset({"/docs", "/docs/oauth2-redirect"})


class SecurityHeadersMiddleware:
    """Set the security headers on every HTTP answer.

    A header that a route has set itself is replaced, so for example
    `Cache-Control` is always `no-store`.

    Args:
        app: The next part of the app that handles the request.
        documentation_enabled: True outside production. Then the Swagger UI
            pages get all headers except `Content-Security-Policy`. In
            production these paths return 404 and get all headers.
    """

    def __init__(self, app: ASGIApp, documentation_enabled: bool) -> None:
        self.app = app
        self.documentation_enabled = documentation_enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Run one request and add the headers to its answer.

        Args:
            scope: Information about the connection, for example its path.
            receive: Reads the next message from the client.
            send: Sends the next message to the client.
        """
        # Only HTTP answers have headers. WebSocket and lifespan pass through.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Choose the headers for this path once, before the answer starts.
        response_headers = dict(SECURITY_HEADERS)
        if self.documentation_enabled and scope["path"] in SWAGGER_UI_PATHS:
            del response_headers[CONTENT_SECURITY_POLICY_HEADER]

        # The headers are in the first message of the answer. We change that
        # message just before it goes to the client.
        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for header_name, header_value in response_headers.items():
                    headers[header_name] = header_value
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
