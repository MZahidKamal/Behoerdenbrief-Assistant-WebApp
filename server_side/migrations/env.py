"""Alembic environment: run migrations with our async engine (DATA_MODEL §9).

`alembic upgrade head` uses `DATABASE_URL` from the settings. A caller can pass
another URL through `config.attributes["database_url"]`; the tests use this for
the test database. No URL is ever written in `alembic.ini`.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from pydantic import SecretStr
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.core.database import Base, create_database_engine

# The Alembic settings from `alembic.ini`, plus values a caller passes in.
config = context.config

# Use the log setup of `alembic.ini` only when Alembic runs as a command. Tests
# keep the app's logging; `disable_existing_loggers=False` never silences
# loggers that already exist.
if config.config_file_name is not None and config.attributes.get(
    "configure_logging", True
):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# The tables that autogenerate compares with the database. Later tasks import
# each feature's `models.py` here, so their tables are part of `Base.metadata`.
target_metadata = Base.metadata


def get_database_url() -> SecretStr:
    """Return the URL to migrate: the one a caller passed, else `DATABASE_URL`.

    Returns:
        The connection string as a secret.
    """
    passed_database_url = config.attributes.get("database_url")
    if isinstance(passed_database_url, SecretStr):
        return passed_database_url
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Write the migration SQL to the screen instead of running it (`--sql`).

    Only the Postgres dialect is needed for this, not a URL, so no password is
    used.
    """
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_with_connection(connection: Connection) -> None:
    """Run the migrations on one open connection, in one transaction.

    Args:
        connection: The database connection.
    """
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Connect with our async engine and run the migrations."""
    database_engine = create_database_engine(get_database_url())
    try:
        async with database_engine.connect() as connection:
            await connection.run_sync(run_migrations_with_connection)
    finally:
        await database_engine.dispose()


# Alembic runs this file for every command. `--sql` means offline mode.
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
