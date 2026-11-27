"""Integration test: the engine really connects to the local test database."""

import allure
import pytest
from sqlalchemy import func, select

from app.core.config import load_settings
from app.core.database import create_database_engine

pytestmark = [allure.feature("server")]

# The name from T-033 and ARCHITECTURE §9.2.
TEST_DATABASE_NAME = "behoerdenbrief_assistant_webapp_testdb"


async def test_database_engine_connects_to_test_database_when_url_is_set() -> None:
    # Arrange: TEST_DATABASE_URL comes from the environment (CI) or from
    # server_side/.env (local computer).
    settings = load_settings()
    if settings.test_database_url is None:
        pytest.fail(
            "TEST_DATABASE_URL is not set. Start the local Supabase, create the "
            "TestDB (README) and set TEST_DATABASE_URL in server_side/.env."
        )
    engine = create_database_engine(settings.test_database_url)

    # Act: ask Postgres which database this connection uses.
    try:
        async with engine.connect() as connection:
            database_name = await connection.scalar(select(func.current_database()))
    finally:
        await engine.dispose()

    # Assert: the test database, never the development database.
    assert database_name == TEST_DATABASE_NAME
