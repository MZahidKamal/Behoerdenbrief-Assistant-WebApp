"""Create the async database engine, the session factory and the table base class.

The API and the worker talk to Postgres only through these objects
(ARCHITECTURE §4, RULES §4.2). Nothing here connects at import time: an engine
opens its first connection only when code uses it.
"""

from pydantic import SecretStr
from sqlalchemy import URL, MetaData, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# SQLAlchemy chooses the driver from the URL scheme. `.env` holds the normal
# `postgresql://` form, so we add the async driver asyncpg here.
ASYNC_DRIVER_NAME = "postgresql+asyncpg"

# Fixed names for indexes and constraints, for example `pk_users`. Alembic
# needs stable names to find and drop a constraint in a later migration.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """The parent class of all table models.

    Every model in a feature's `models.py` inherits from it (DATA_MODEL §10),
    so all tables share one `MetaData` with the naming convention above.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def build_async_database_url(database_url: SecretStr) -> URL:
    """Turn a `postgresql://` connection string into one for asyncpg.

    Args:
        database_url: The checked connection string from the settings.

    Returns:
        The same address with the driver `postgresql+asyncpg`. A `URL` object
        hides the password when it is printed.
    """
    return make_url(database_url.get_secret_value()).set(drivername=ASYNC_DRIVER_NAME)


def create_database_engine(database_url: SecretStr) -> AsyncEngine:
    """Create the async engine with its pool of database connections.

    Args:
        database_url: The connection string, normally `settings.database_url`.
            Tests pass `settings.test_database_url`.

    Returns:
        The engine. It connects only when code uses it.
    """
    # `pool_pre_ping`: test a connection before use, so a connection that the
    # database has closed (restart, idle timeout) is replaced, not used.
    return create_async_engine(
        build_async_database_url(database_url),
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create the factory that gives each request or task its own session.

    Args:
        engine: The engine from `create_database_engine`.

    Returns:
        The session factory. `get_database_session` (T-035) uses it.
    """
    # `expire_on_commit=False`: after a commit, the loaded objects keep their
    # values. Otherwise reading a field would start a hidden database call,
    # and in async code that raises an error.
    return async_sessionmaker(engine, expire_on_commit=False)
