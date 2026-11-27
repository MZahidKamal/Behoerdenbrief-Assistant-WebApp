"""Integration tests: after-commit callbacks with a real session on the TestDB."""

from collections.abc import AsyncIterator

import allure
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import load_settings
from app.core.database import (
    commit_and_run_after_commit_callbacks,
    create_database_engine,
    create_session_factory,
    discard_after_commit_callbacks,
    run_after_commit,
)

pytestmark = [allure.feature("server")]


@pytest.fixture
async def test_database_session() -> AsyncIterator[AsyncSession]:
    """Give a real session on the test database.

    Yields:
        A session with an open transaction.
    """
    settings = load_settings()
    if settings.test_database_url is None:
        pytest.fail(
            "TEST_DATABASE_URL is not set. Start the local Supabase, create the "
            "TestDB (README) and set TEST_DATABASE_URL in server_side/.env."
        )
    engine = create_database_engine(settings.test_database_url)
    try:
        async with create_session_factory(engine)() as session:
            # A small query opens a real transaction on the server.
            await session.execute(select(1))
            yield session
    finally:
        await engine.dispose()


async def test_callback_runs_when_real_commit_succeeds(
    test_database_session: AsyncSession,
) -> None:
    # Arrange
    called_names: list[str] = []

    async def record_call() -> None:
        called_names.append("called")

    run_after_commit(test_database_session, record_call)

    # Act
    await commit_and_run_after_commit_callbacks(test_database_session)

    # Assert
    assert called_names == ["called"]


async def test_callback_does_not_run_when_real_transaction_is_rolled_back(
    test_database_session: AsyncSession,
) -> None:
    # Arrange
    called_names: list[str] = []

    async def record_call() -> None:
        called_names.append("called")

    run_after_commit(test_database_session, record_call)

    # Act: the same steps as `get_database_session` on an error.
    discard_after_commit_callbacks(test_database_session)
    await test_database_session.rollback()
    await commit_and_run_after_commit_callbacks(test_database_session)

    # Assert
    assert called_names == []
