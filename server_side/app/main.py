"""Create the FastAPI app: middleware, routers, the health check and the MCP server.

Start it locally with `uv run uvicorn app.main:app --reload` (ARCHITECTURE §12).
"""

from fastapi import FastAPI

from app.core.config import get_settings


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
    get_settings()

    # The title and summary are shown in the API documentation (/docs).
    return FastAPI(
        title="Behördenbrief Assistant API",
        summary="Helps Bengali-speaking people understand and answer German letters.",
    )


# Uvicorn looks for this variable: `uvicorn app.main:app`.
app = create_app()
