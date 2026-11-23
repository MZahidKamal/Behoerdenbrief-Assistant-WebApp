"""Create the FastAPI app: middleware, routers, the health check and the MCP server.

Start it locally with `uv run uvicorn app.main:app --reload` (ARCHITECTURE §12).
"""

from typing import Literal

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.request_size_limit import RequestSizeLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware

# CORS rules (SECURITY §12, MEMORY D-112). Only the methods of API_DESIGN.
# Only the headers the frontend sends: the login token and the body type.
# The frontend may read `Retry-After` after `429 rate_limited` (API_DESIGN §1.9).
CORS_ALLOWED_METHODS = ("GET", "POST", "PATCH", "DELETE")
CORS_ALLOWED_HEADERS = ("Authorization", "Content-Type")
CORS_EXPOSED_HEADERS = ("Retry-After",)


class HealthResponse(BaseModel):
    """The answer of the health check.

    Attributes:
        status: Always `ok`. The endpoint is public, so it returns no other
            data (API_DESIGN §1.1).
    """

    status: Literal["ok"]


# The health check belongs to no feature, so it lives here (ARCHITECTURE §4.1).
health_router = APIRouter(tags=["health"])


@health_router.get("/health", operation_id="get_health")
async def get_health() -> HealthResponse:
    """Tell Docker and Render that the app is alive.

    Returns:
        Always `{"status": "ok"}`.
    """
    return HealthResponse(status="ok")


def create_app() -> FastAPI:
    """Build a new FastAPI app with all its parts.

    Later tasks add routers, middleware and error handlers here.

    Returns:
        A new app, ready for Uvicorn or for tests.

    Raises:
        InvalidSettingsError: A required setting is missing, or a setting has
            a wrong value.
    """
    # Read the settings first. If one is missing or wrong, the app stops
    # here with a clear message, before it can run in a broken state.
    settings = get_settings()

    # Set up the log format next, so every later step can already log.
    configure_logging(settings)

    # The API documentation is a full map of all endpoints. It helps us while
    # we build, but in production it would only help an attacker, so there
    # `/docs` and `/openapi.json` do not exist and return 404 (SECURITY §12).
    is_production = settings.app_env == "production"

    # The title and summary are shown in /docs. We use only Swagger UI
    # (/docs), so the second docs page ReDoc is off everywhere (MEMORY D-109).
    application = FastAPI(
        title="Behördenbrief Assistant API",
        summary="Helps Bengali-speaking people understand and answer German letters.",
        docs_url=None if is_production else "/docs",
        openapi_url=None if is_production else "/openapi.json",
        redoc_url=None,
    )

    # Give every request its own id, so all log lines of one request can be
    # found together (RULES §8).
    application.add_middleware(RequestIdMiddleware)

    # Stop very large request bodies at `MAX_UPLOAD_REQUEST_MB`, so one
    # request cannot fill the server's memory (API_DESIGN §1.8).
    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_upload_request_mb=settings.max_upload_request_mb,
    )

    # Only our frontend may read API answers in a browser (SECURITY §12).
    # No cookies are used (Bearer tokens), so no credentials. CORS is only a
    # browser rule; it never replaces the login check. It is added before the
    # security headers, so it runs inside them and its preflight answers also
    # get those headers.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
        expose_headers=CORS_EXPOSED_HEADERS,
    )

    # Add `Cache-Control: no-store` and the security headers to every answer
    # (SECURITY §12). Swagger UI keeps working outside production.
    application.add_middleware(
        SecurityHeadersMiddleware, documentation_enabled=not is_production
    )

    # Turn every error into one standard form: Problem Details (API_DESIGN §3).
    register_exception_handlers(application, settings)

    # Connect the routes. `/health` has no `/api/v1` prefix (API_DESIGN §1.1).
    application.include_router(health_router)

    return application


# Uvicorn looks for this variable: `uvicorn app.main:app`.
app = create_app()
