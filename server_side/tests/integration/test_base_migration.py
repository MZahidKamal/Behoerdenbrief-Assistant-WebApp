"""Integration tests: the base migration (T-038) on the TestDB.

The tests run the real migrations in `migrations/versions/`. After each test
the TestDB goes back to `base`, so other migration tests start clean.

The tests are normal `def` functions, not `async def`, for the same reason as
in `test_alembic_migrations.py`: our `env.py` calls `asyncio.run(...)`.
"""

import asyncio
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import allure
import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import text

from app.core.database import create_database_engine

pytestmark = [allure.feature("server")]

# `server_side/alembic.ini`: two folders up from `tests/integration/`.
ALEMBIC_CONFIGURATION_FILE = Path(__file__).resolve().parents[2] / "alembic.ini"

# The roles of the Supabase Data API (MEMORY D-058).
DATA_API_ROLE_NAMES = ("anon", "authenticated", "service_role")

# The default rights that the local development database gives these roles
# before the base migration runs (checked on 2026-11-28).
OPEN_DEFAULT_RIGHTS_STATEMENTS = [
    "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
    f"GRANT ALL ON {object_type} TO anon, authenticated, service_role"
    for object_type in ("TABLES", "SEQUENCES", "FUNCTIONS")
]
CLOSED_DEFAULT_RIGHTS_STATEMENTS = [
    "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
    f"REVOKE ALL ON {object_type} FROM anon, authenticated, service_role"
    for object_type in ("TABLES", "SEQUENCES", "FUNCTIONS")
]


async def _execute_statements(database_url: SecretStr, statements: list[str]) -> None:
    engine = create_database_engine(database_url)
    try:
        async with engine.begin() as connection:
            for statement in statements:
                await connection.execute(text(statement))
    finally:
        await engine.dispose()


async def _read_vector_extension_schema(database_url: SecretStr) -> str | None:
    engine = create_database_engine(database_url)
    try:
        async with engine.connect() as connection:
            # Raw SQL gives an untyped value, so turn it into `str` here.
            schema_name = await connection.scalar(
                text(
                    "SELECT extnamespace::regnamespace::text FROM pg_extension "
                    "WHERE extname = 'vector'"
                )
            )
            return None if schema_name is None else str(schema_name)
    finally:
        await engine.dispose()


async def _read_set_updated_at_settings(database_url: SecretStr) -> list[str] | None:
    engine = create_database_engine(database_url)
    try:
        async with engine.connect() as connection:
            # `proconfig` holds the `SET` options of the function. A missing
            # function gives no row, so the result is `None`.
            result = await connection.execute(
                text(
                    "SELECT coalesce(proconfig, '{}') FROM pg_proc "
                    "WHERE proname = 'set_updated_at' "
                    "AND pronamespace = 'public'::regnamespace"
                )
            )
            row = result.first()
            return None if row is None else list(row[0])
    finally:
        await engine.dispose()


async def _read_extensions_schema_exists(database_url: SecretStr) -> bool:
    engine = create_database_engine(database_url)
    try:
        async with engine.connect() as connection:
            return bool(
                await connection.scalar(
                    text(
                        "SELECT EXISTS (SELECT FROM pg_namespace "
                        "WHERE nspname = 'extensions')"
                    )
                )
            )
    finally:
        await engine.dispose()


async def _update_row_with_trigger(
    database_url: SecretStr,
) -> tuple[datetime, datetime]:
    engine = create_database_engine(database_url)
    try:
        async with engine.connect() as connection:
            # A temporary table with an old `updated_at` and the trigger, the
            # same way later table migrations attach it.
            await connection.execute(
                text(
                    "CREATE TEMPORARY TABLE trigger_check_rows ("
                    "id integer PRIMARY KEY, name text NOT NULL, "
                    "updated_at timestamptz NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "CREATE TRIGGER set_updated_at_on_trigger_check_rows "
                    "BEFORE UPDATE ON trigger_check_rows FOR EACH ROW "
                    "EXECUTE FUNCTION public.set_updated_at()"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO trigger_check_rows VALUES "
                    "(1, 'old name', '2000-01-01T00:00:00+00:00')"
                )
            )

            # The UPDATE does not set `updated_at`; the trigger must do it.
            await connection.execute(
                text("UPDATE trigger_check_rows SET name = 'new name' WHERE id = 1")
            )
            result = await connection.execute(
                text("SELECT updated_at, now() FROM trigger_check_rows WHERE id = 1")
            )
            updated_at, transaction_time = result.one()

            # Roll back, so the TestDB keeps nothing of this check.
            await connection.rollback()
            return updated_at, transaction_time
    finally:
        await engine.dispose()


async def _read_new_table_rights(database_url: SecretStr) -> dict[str, bool]:
    engine = create_database_engine(database_url)
    try:
        async with engine.connect() as connection:
            # A new table in `public`, created by `postgres` like a migration.
            await connection.execute(
                text("CREATE TABLE public.default_rights_check_rows (id integer)")
            )

            # `has_table_privilege` with a list is true if the role has any one
            # of these rights.
            rights_by_role_name: dict[str, bool] = {}
            for role_name in DATA_API_ROLE_NAMES:
                rights_by_role_name[role_name] = bool(
                    await connection.scalar(
                        text(
                            "SELECT has_table_privilege(:role_name, "
                            "'public.default_rights_check_rows', "
                            "'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, "
                            "REFERENCES, TRIGGER')"
                        ),
                        {"role_name": role_name},
                    )
                )

            # Roll back, so the check table is never kept.
            await connection.rollback()
            return rights_by_role_name
    finally:
        await engine.dispose()


@pytest.fixture
def alembic_configuration_for_test_database(
    test_database_url: SecretStr,
) -> Iterator[Config]:
    """Give an Alembic configuration with the real migrations for the TestDB.

    After the test, the database always goes back to `base`, also when the
    test failed halfway.

    Args:
        test_database_url: The checked TestDB URL from `conftest.py`.

    Yields:
        The configuration. Pass it to `alembic.command` functions.
    """
    # Our real alembic.ini and the real `migrations/versions/` folder.
    alembic_configuration = Config(ALEMBIC_CONFIGURATION_FILE)
    alembic_configuration.attributes["database_url"] = test_database_url
    alembic_configuration.attributes["configure_logging"] = False

    try:
        yield alembic_configuration
    finally:
        command.downgrade(alembic_configuration, "base")


@pytest.fixture
def test_database_with_open_default_rights(
    test_database_url: SecretStr,
) -> Iterator[None]:
    """Give the TestDB the open default rights of the development database.

    The TestDB has no default rights of its own. Without this setup, a test
    of the revoke would pass even if the revoke did nothing.

    Args:
        test_database_url: The checked TestDB URL from `conftest.py`.

    Yields:
        Nothing; the TestDB has the open default rights during the test.
    """
    asyncio.run(_execute_statements(test_database_url, OPEN_DEFAULT_RIGHTS_STATEMENTS))

    # Always close the rights again, also when the migration failed.
    try:
        yield
    finally:
        asyncio.run(
            _execute_statements(test_database_url, CLOSED_DEFAULT_RIGHTS_STATEMENTS)
        )


def test_upgrade_head_enables_vector_extension_when_base_migration_runs(
    alembic_configuration_for_test_database: Config,
    test_database_url: SecretStr,
) -> None:
    # Act
    command.upgrade(alembic_configuration_for_test_database, "head")

    # Assert
    vector_extension_schema = asyncio.run(
        _read_vector_extension_schema(test_database_url)
    )
    assert vector_extension_schema == "extensions"


def test_upgrade_head_creates_set_updated_at_function_when_base_migration_runs(
    alembic_configuration_for_test_database: Config,
    test_database_url: SecretStr,
) -> None:
    # Act
    command.upgrade(alembic_configuration_for_test_database, "head")

    # Assert: the function exists and has its fixed, empty search path.
    function_settings = asyncio.run(_read_set_updated_at_settings(test_database_url))
    assert function_settings == ['search_path=""']


def test_set_updated_at_sets_new_time_when_row_is_updated(
    alembic_configuration_for_test_database: Config,
    test_database_url: SecretStr,
) -> None:
    # Arrange
    command.upgrade(alembic_configuration_for_test_database, "head")

    # Act
    updated_at, transaction_time = asyncio.run(
        _update_row_with_trigger(test_database_url)
    )

    # Assert: `now()` is the start time of the transaction, so both are equal.
    assert updated_at == transaction_time


def test_upgrade_head_closes_default_rights_when_dev_database_had_them(
    alembic_configuration_for_test_database: Config,
    test_database_with_open_default_rights: None,
    test_database_url: SecretStr,
) -> None:
    # Act
    command.upgrade(alembic_configuration_for_test_database, "head")

    # Assert: a new table gives no Data API role any right.
    rights_by_role_name = asyncio.run(_read_new_table_rights(test_database_url))
    assert rights_by_role_name == dict.fromkeys(DATA_API_ROLE_NAMES, False)


def test_downgrade_base_removes_function_and_extension_when_base_migration_was_applied(
    alembic_configuration_for_test_database: Config,
    test_database_url: SecretStr,
) -> None:
    # Arrange
    command.upgrade(alembic_configuration_for_test_database, "head")

    # Act
    command.downgrade(alembic_configuration_for_test_database, "base")

    # Assert: function and extension are gone; the schema stays (DATA_MODEL §9).
    assert asyncio.run(_read_set_updated_at_settings(test_database_url)) is None
    assert asyncio.run(_read_vector_extension_schema(test_database_url)) is None
    assert asyncio.run(_read_extensions_schema_exists(test_database_url)) is True


def test_downgrade_base_keeps_default_rights_closed_when_base_migration_was_applied(
    alembic_configuration_for_test_database: Config,
    test_database_with_open_default_rights: None,
    test_database_url: SecretStr,
) -> None:
    # Arrange
    command.upgrade(alembic_configuration_for_test_database, "head")

    # Act
    command.downgrade(alembic_configuration_for_test_database, "base")

    # Assert: the exception to RULES §9 (MEMORY D-058): no rights come back.
    rights_by_role_name = asyncio.run(_read_new_table_rights(test_database_url))
    assert rights_by_role_name == dict.fromkeys(DATA_API_ROLE_NAMES, False)


def test_upgrade_head_works_again_when_base_migration_was_downgraded(
    alembic_configuration_for_test_database: Config,
    test_database_url: SecretStr,
) -> None:
    # Arrange: up and down once (RULES §9: upgrade, downgrade, upgrade).
    command.upgrade(alembic_configuration_for_test_database, "head")
    command.downgrade(alembic_configuration_for_test_database, "base")

    # Act
    command.upgrade(alembic_configuration_for_test_database, "head")

    # Assert
    assert asyncio.run(_read_vector_extension_schema(test_database_url)) == (
        "extensions"
    )
    assert asyncio.run(_read_set_updated_at_settings(test_database_url)) == [
        'search_path=""'
    ]
