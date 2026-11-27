"""Unit tests for the engine, sessions and table base in `app/core/database.py`."""

import logging
from typing import ClassVar

import allure
import pytest
from pydantic import SecretStr
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.schema import CreateTable

from app.core.database import (
    NAMING_CONVENTION,
    Base,
    build_async_database_url,
    commit_and_run_after_commit_callbacks,
    create_database_engine,
    create_session_factory,
    discard_after_commit_callbacks,
    run_after_commit,
)

pytestmark = [allure.feature("server")]

EXAMPLE_DATABASE_URL = SecretStr(
    "postgresql://example_user:example_password"
    "@database.example.test:5432/example_database"
)


class FakeCommitSession(AsyncSession):
    """A session whose commit does nothing, or fails when the test asks."""

    fail_on_commit: ClassVar[bool] = False

    async def commit(self) -> None:
        """Do nothing, or fail when the test asks for it.

        Raises:
            RuntimeError: `fail_on_commit` is set.
        """
        if FakeCommitSession.fail_on_commit:
            raise RuntimeError("Example commit failure")


@pytest.fixture
def fake_session() -> FakeCommitSession:
    """Give a new fake session that commits without errors.

    Returns:
        The fake session. It never uses a database.
    """
    FakeCommitSession.fail_on_commit = False
    return FakeCommitSession()


def test_build_async_database_url_uses_asyncpg_when_url_is_plain_postgresql() -> None:
    # Act
    async_database_url = build_async_database_url(EXAMPLE_DATABASE_URL)

    # Assert: only the driver changes; user, password, host, port and
    # database name stay the same.
    assert async_database_url.render_as_string(hide_password=False) == (
        "postgresql+asyncpg://example_user:example_password"
        "@database.example.test:5432/example_database"
    )


def test_build_async_database_url_hides_password_when_url_is_printed() -> None:
    # Act
    async_database_url = build_async_database_url(EXAMPLE_DATABASE_URL)

    # Assert
    assert "example_password" not in str(async_database_url)
    assert "example_password" not in repr(async_database_url)


async def test_create_database_engine_uses_asyncpg_driver_when_called() -> None:
    # Act: creating an engine does not connect, so no database is needed.
    engine = create_database_engine(EXAMPLE_DATABASE_URL)

    # Assert
    try:
        assert engine.dialect.driver == "asyncpg"
        assert engine.url.database == "example_database"
    finally:
        await engine.dispose()


async def test_create_session_factory_keeps_values_after_commit_when_called() -> None:
    # Arrange
    engine = create_database_engine(EXAMPLE_DATABASE_URL)

    # Act
    session_factory = create_session_factory(engine)

    # Assert
    try:
        assert session_factory.kw["expire_on_commit"] is False
        assert session_factory.kw["bind"] is engine
    finally:
        await engine.dispose()


def test_base_uses_naming_convention_when_tables_are_defined() -> None:
    # Assert: all models share the metadata with our naming convention.
    assert Base.metadata.naming_convention == NAMING_CONVENTION


async def test_naming_convention_names_constraints_when_table_is_created() -> None:
    # Arrange: a separate MetaData, so no example table is added to `Base`.
    # Our engine gives the real Postgres dialect; it does not connect.
    engine = create_database_engine(EXAMPLE_DATABASE_URL)
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    Table("example_owners", metadata, Column("id", Integer, primary_key=True))
    example_items = Table(
        "example_items",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("owner_id", Integer, ForeignKey("example_owners.id"), unique=True),
    )

    # Act: the SQL that Postgres would receive.
    try:
        create_table_sql = str(
            CreateTable(example_items).compile(dialect=engine.dialect)
        )
    finally:
        await engine.dispose()

    # Assert
    assert "CONSTRAINT pk_example_items PRIMARY KEY" in create_table_sql
    assert "CONSTRAINT uq_example_items_owner_id UNIQUE" in create_table_sql
    assert (
        "CONSTRAINT fk_example_items_owner_id_example_owners FOREIGN KEY"
        in create_table_sql
    )


async def test_commit_runs_callbacks_in_order_when_commit_succeeds(
    fake_session: FakeCommitSession,
) -> None:
    # Arrange
    called_names: list[str] = []

    async def first_callback() -> None:
        called_names.append("first")

    async def second_callback() -> None:
        called_names.append("second")

    run_after_commit(fake_session, first_callback)
    run_after_commit(fake_session, second_callback)

    # Act
    await commit_and_run_after_commit_callbacks(fake_session)

    # Assert
    assert called_names == ["first", "second"]


async def test_commit_runs_callback_once_when_committed_twice(
    fake_session: FakeCommitSession,
) -> None:
    # Arrange
    called_names: list[str] = []

    async def record_call() -> None:
        called_names.append("called")

    run_after_commit(fake_session, record_call)

    # Act
    await commit_and_run_after_commit_callbacks(fake_session)
    await commit_and_run_after_commit_callbacks(fake_session)

    # Assert: the first commit used the callback up.
    assert called_names == ["called"]


async def test_commit_skips_callbacks_when_commit_fails(
    fake_session: FakeCommitSession,
) -> None:
    # Arrange
    called_names: list[str] = []

    async def record_call() -> None:
        called_names.append("called")

    run_after_commit(fake_session, record_call)
    FakeCommitSession.fail_on_commit = True

    # Act
    with pytest.raises(RuntimeError):
        await commit_and_run_after_commit_callbacks(fake_session)
    FakeCommitSession.fail_on_commit = False
    await commit_and_run_after_commit_callbacks(fake_session)

    # Assert: nothing ran, and the failed commit threw the callback away, so
    # the later successful commit does not run it either.
    assert called_names == []


async def test_discard_removes_callbacks_when_work_is_rolled_back(
    fake_session: FakeCommitSession,
) -> None:
    # Arrange
    called_names: list[str] = []

    async def record_call() -> None:
        called_names.append("called")

    run_after_commit(fake_session, record_call)

    # Act
    discard_after_commit_callbacks(fake_session)
    await commit_and_run_after_commit_callbacks(fake_session)

    # Assert
    assert called_names == []


async def test_commit_logs_error_and_continues_when_callback_fails(
    fake_session: FakeCommitSession, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange: the first callback fails, the second records its call.
    called_names: list[str] = []

    async def failing_callback() -> None:
        raise RuntimeError("Example callback failure")

    async def record_call() -> None:
        called_names.append("called")

    run_after_commit(fake_session, failing_callback)
    run_after_commit(fake_session, record_call)

    # Act: no error comes out, because the data is already committed.
    with caplog.at_level(logging.ERROR, logger="app.core.database"):
        await commit_and_run_after_commit_callbacks(fake_session)

    # Assert: the next callback still ran, and the failure was logged at
    # error level with its traceback.
    assert called_names == ["called"]
    error_records = [
        record
        for record in caplog.records
        if record.name == "app.core.database" and record.levelno == logging.ERROR
    ]
    assert len(error_records) == 1
    assert "after-commit callback failed" in error_records[0].getMessage()
    assert error_records[0].exc_info is not None
