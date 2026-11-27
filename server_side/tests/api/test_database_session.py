"""API tests: `DatabaseSession` commits on success and rolls back on errors.

The real app runs with all its error handlers; only the session is a fake, so
no database is needed (RULES §4.2, MEMORY D-056).
"""

from collections.abc import AsyncIterator
from typing import ClassVar

import allure
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import run_after_commit
from app.core.dependencies import DatabaseSession
from app.core.exceptions import AppException
from app.main import create_app

# Allure groups the results by feature. The database session belongs to no feature.
pytestmark = [allure.feature("server")]


class ExampleItemNotFoundError(AppException):
    """An invented error, only for these tests."""

    code = "not_found"
    status = 404
    title = "Resource not found"


class FakeSession(AsyncSession):
    """A session that only counts its calls and never uses a database.

    The counters are class values, because the dependency creates the session
    itself; the test reads them through the class.
    """

    commit_count: ClassVar[int] = 0
    rollback_count: ClassVar[int] = 0
    fail_on_commit: ClassVar[bool] = False

    async def commit(self) -> None:
        """Count the commit, or fail when the test asks for it.

        Raises:
            RuntimeError: `fail_on_commit` is set.
        """
        FakeSession.commit_count += 1
        if FakeSession.fail_on_commit:
            raise RuntimeError("Example commit failure")

    async def rollback(self) -> None:
        """Count the rollback."""
        FakeSession.rollback_count += 1

    async def close(self) -> None:
        """Do nothing: there is no connection to close."""


# For each after-commit callback that ran: the commit count at that moment.
commit_counts_seen_by_callbacks: list[int] = []


async def record_commit_count() -> None:
    """An after-commit callback that notes how many commits happened before it."""
    commit_counts_seen_by_callbacks.append(FakeSession.commit_count)


@pytest.fixture
async def fake_session_client() -> AsyncIterator[AsyncClient]:
    """Give an HTTP client for the real app with a fake session and test routes.

    Yields:
        A client that talks to the app in memory.
    """
    # Start every test with fresh counters.
    FakeSession.commit_count = 0
    FakeSession.rollback_count = 0
    FakeSession.fail_on_commit = False
    commit_counts_seen_by_callbacks.clear()

    # The real app, but its sessions come from a factory for the fake.
    application = create_app()
    application.state.database_session_factory = async_sessionmaker(class_=FakeSession)

    @application.get("/test/success")
    async def get_success_example(database_session: DatabaseSession) -> None:
        return None

    @application.get("/test/app-exception")
    async def get_app_exception_example(database_session: DatabaseSession) -> None:
        raise ExampleItemNotFoundError()

    @application.get("/test/http-exception")
    async def get_http_exception_example(database_session: DatabaseSession) -> None:
        raise HTTPException(status_code=403, detail="Example forbidden.")

    @application.get("/test/callback")
    async def get_callback_example(database_session: DatabaseSession) -> None:
        run_after_commit(database_session, record_commit_count)

    @application.get("/test/callback-error")
    async def get_callback_error_example(database_session: DatabaseSession) -> None:
        run_after_commit(database_session, record_commit_count)
        raise ExampleItemNotFoundError()

    # After a crash, Starlette sends the 500 answer and then raises the error
    # again. `raise_app_exceptions=False` lets the client return the answer,
    # like a real server does.
    async with AsyncClient(
        transport=ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client


async def test_database_session_commits_when_route_succeeds(
    fake_session_client: AsyncClient,
) -> None:
    # Act
    response = await fake_session_client.get("/test/success")

    # Assert
    assert response.status_code == 200
    assert FakeSession.commit_count == 1
    assert FakeSession.rollback_count == 0


async def test_database_session_rolls_back_when_route_raises_app_exception(
    fake_session_client: AsyncClient,
) -> None:
    # Act
    response = await fake_session_client.get("/test/app-exception")

    # Assert: the error handler still answers, and nothing was committed.
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert FakeSession.commit_count == 0
    assert FakeSession.rollback_count == 1


async def test_database_session_rolls_back_when_route_raises_http_exception(
    fake_session_client: AsyncClient,
) -> None:
    # Act
    response = await fake_session_client.get("/test/http-exception")

    # Assert
    assert response.status_code == 403
    assert FakeSession.commit_count == 0
    assert FakeSession.rollback_count == 1


async def test_database_session_returns_500_when_commit_fails(
    fake_session_client: AsyncClient,
) -> None:
    # Arrange
    FakeSession.fail_on_commit = True

    # Act
    response = await fake_session_client.get("/test/success")

    # Assert: the commit runs before the answer, so the user sees the failure
    # and never a false success.
    assert response.status_code == 500
    assert FakeSession.commit_count == 1


async def test_database_session_runs_callback_after_commit_when_route_succeeds(
    fake_session_client: AsyncClient,
) -> None:
    # Act
    response = await fake_session_client.get("/test/callback")

    # Assert: the callback ran once, and the commit had already happened.
    assert response.status_code == 200
    assert commit_counts_seen_by_callbacks == [1]


async def test_database_session_skips_callback_when_route_raises(
    fake_session_client: AsyncClient,
) -> None:
    # Act
    response = await fake_session_client.get("/test/callback-error")

    # Assert
    assert response.status_code == 404
    assert commit_counts_seen_by_callbacks == []
