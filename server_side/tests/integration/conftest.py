"""Shared fixtures for the integration tests against the local TestDB."""

import asyncio

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.config import load_settings
from app.core.database import create_database_engine

# The name from T-033 and ARCHITECTURE §9.2.
TEST_DATABASE_NAME = "behoerdenbrief_assistant_webapp_testdb"


async def _read_current_database_name(database_url: SecretStr) -> str | None:
    engine = create_database_engine(database_url)
    try:
        async with engine.connect() as connection:
            return await connection.scalar(select(func.current_database()))
    finally:
        await engine.dispose()


@pytest.fixture
def test_database_url() -> SecretStr:
    """Give the URL of the TestDB, after a check that it really is the TestDB.

    Tests that change the schema (migrations) must never run on another
    database, even when `TEST_DATABASE_URL` is set wrong.

    Returns:
        The connection string as a secret, so it is never printed.
    """
    # The TestDB URL comes from the environment (CI) or server_side/.env.
    settings = load_settings()
    if settings.test_database_url is None:
        pytest.fail(
            "TEST_DATABASE_URL is not set. Start the local Supabase, create the "
            "TestDB (README) and set TEST_DATABASE_URL in server_side/.env."
        )

    # Safety: ask Postgres which database the URL really points to.
    current_database_name = asyncio.run(
        _read_current_database_name(settings.test_database_url)
    )
    if current_database_name != TEST_DATABASE_NAME:
        pytest.fail(
            f"TEST_DATABASE_URL points to {current_database_name!r}, "
            f"not to {TEST_DATABASE_NAME!r}. No test was run on it."
        )
    return settings.test_database_url
