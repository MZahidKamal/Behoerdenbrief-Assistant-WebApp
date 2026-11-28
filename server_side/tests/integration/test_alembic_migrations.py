"""Integration tests: Alembic runs an empty migration up and down on the TestDB.

The tests use our real `alembic.ini`, `migrations/env.py` and
`migrations/script.py.mako`. Only the migration file itself lives in a
temporary folder, so the real `migrations/versions/` is never touched.

The tests are normal `def` functions, not `async def`. Our `env.py` calls
`asyncio.run(...)`, like the real `alembic upgrade head` command, and that
cannot start inside the event loop that pytest-asyncio runs for async tests.
"""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import allure
import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import column, inspect, select, table

from app.core.database import create_database_engine

pytestmark = [allure.feature("server")]

# `server_side/alembic.ini`: two folders up from `tests/integration/`.
ALEMBIC_CONFIGURATION_FILE = Path(__file__).resolve().parents[2] / "alembic.ini"

# A fixed id, so a run that stopped halfway can still be cleaned up next time.
EMPTY_MIGRATION_REVISION_ID = "empty_test_migration"

# Alembic's own table that stores which migration the database is at.
ALEMBIC_VERSION_TABLE_NAME = "alembic_version"


async def _read_applied_revision_ids(database_url: SecretStr) -> list[str]:
    engine = create_database_engine(database_url)
    try:
        async with engine.connect() as connection:
            # Before the first migration the table does not exist yet.
            has_version_table = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).has_table(
                    ALEMBIC_VERSION_TABLE_NAME
                )
            )
            if not has_version_table:
                return []

            alembic_version_table = table(
                ALEMBIC_VERSION_TABLE_NAME, column("version_num")
            )
            result = await connection.scalars(
                select(alembic_version_table.c.version_num)
            )
            return [str(revision_id) for revision_id in result]
    finally:
        await engine.dispose()


@pytest.fixture
def alembic_configuration_with_empty_migration(
    tmp_path: Path, test_database_url: SecretStr
) -> Iterator[Config]:
    """Give an Alembic configuration for the TestDB with one empty migration.

    After the test, the database always goes back to `base`, also when the
    test failed halfway.

    Args:
        tmp_path: A new temporary folder from pytest for the migration file.
        test_database_url: The checked TestDB URL from `conftest.py`.

    Yields:
        The configuration. Pass it to `alembic.command` functions.
    """
    # Our real alembic.ini, but migration files only in the temporary folder.
    # `env.py` reads the URL from `database_url` and keeps the test logging.
    alembic_configuration = Config(ALEMBIC_CONFIGURATION_FILE)
    alembic_configuration.set_main_option("version_locations", str(tmp_path))
    alembic_configuration.attributes["database_url"] = test_database_url
    alembic_configuration.attributes["configure_logging"] = False

    # An empty migration made from our template, the same way as
    # `alembic revision -m ...`. Alembic must load it, so this also checks
    # that the template gives valid Python.
    command.revision(
        alembic_configuration,
        message="empty test migration",
        rev_id=EMPTY_MIGRATION_REVISION_ID,
    )

    # Always clean up, so the TestDB never keeps the id of a temporary file.
    # Otherwise later migrations (T-039) fail with "Can't locate revision".
    try:
        yield alembic_configuration
    finally:
        command.downgrade(alembic_configuration, "base")


def test_upgrade_head_records_revision_when_empty_migration_exists(
    alembic_configuration_with_empty_migration: Config,
    test_database_url: SecretStr,
) -> None:
    # Act
    command.upgrade(alembic_configuration_with_empty_migration, "head")

    # Assert
    applied_revision_ids = asyncio.run(_read_applied_revision_ids(test_database_url))
    assert applied_revision_ids == [EMPTY_MIGRATION_REVISION_ID]


def test_downgrade_base_removes_revision_when_empty_migration_was_applied(
    alembic_configuration_with_empty_migration: Config,
    test_database_url: SecretStr,
) -> None:
    # Arrange
    command.upgrade(alembic_configuration_with_empty_migration, "head")

    # Act
    command.downgrade(alembic_configuration_with_empty_migration, "base")

    # Assert
    applied_revision_ids = asyncio.run(_read_applied_revision_ids(test_database_url))
    assert applied_revision_ids == []


def test_upgrade_head_works_again_when_migration_was_downgraded(
    alembic_configuration_with_empty_migration: Config,
    test_database_url: SecretStr,
) -> None:
    # Arrange: up and down once (RULES §9: upgrade, downgrade, upgrade).
    command.upgrade(alembic_configuration_with_empty_migration, "head")
    command.downgrade(alembic_configuration_with_empty_migration, "base")

    # Act
    command.upgrade(alembic_configuration_with_empty_migration, "head")

    # Assert
    applied_revision_ids = asyncio.run(_read_applied_revision_ids(test_database_url))
    assert applied_revision_ids == [EMPTY_MIGRATION_REVISION_ID]
