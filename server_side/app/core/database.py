"""Create the async database engine, the session factory and the table base class.

The API and the worker talk to Postgres only through these objects
(ARCHITECTURE §4, RULES §4.2). Nothing here connects at import time: an engine
opens its first connection only when code uses it.
"""

import logging
from collections.abc import Awaitable, Callable

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

# The key in `session.info` (SQLAlchemy's place for our own data per session).
AFTER_COMMIT_CALLBACKS_KEY = "after_commit_callbacks"

# A callback takes no arguments and is async, so it can enqueue a task without
# blocking the event loop (RULES §4.3).
AfterCommitCallback = Callable[[], Awaitable[None]]

logger = logging.getLogger(__name__)


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


def run_after_commit(session: AsyncSession, callback: AfterCommitCallback) -> None:
    """Run `callback` only after this session's next successful commit.

    Services use it to enqueue Celery tasks, so a worker never reads a row
    that is not committed yet (RULES §4.2, MEMORY D-057). On a rollback the
    callback is thrown away.

    Args:
        session: The session of the current request or task.
        callback: An async function without arguments, for example
            `lambda: enqueue_process_letter(letter_id)`.
    """
    session.info.setdefault(AFTER_COMMIT_CALLBACKS_KEY, []).append(callback)


def discard_after_commit_callbacks(session: AsyncSession) -> None:
    """Throw away all waiting callbacks, because the work was rolled back.

    Args:
        session: The session of the current request or task.
    """
    session.info.pop(AFTER_COMMIT_CALLBACKS_KEY, None)


async def commit_and_run_after_commit_callbacks(session: AsyncSession) -> None:
    """Commit the session, then run its waiting callbacks in order.

    `get_database_session` (API) and later `run_async` (worker, T-122) commit
    only through this function. A failed callback does not undo the commit:
    the data is saved, so it is logged at error level and the next callbacks
    still run (MEMORY D-057). Rows whose task never started are restarted by
    T-389.

    Args:
        session: The session of the current request or task.

    Raises:
        Exception: The commit failed. The callbacks are thrown away.
    """
    try:
        await session.commit()
    except Exception:
        # Nothing was saved, so no callback may run.
        discard_after_commit_callbacks(session)
        raise

    callbacks: list[AfterCommitCallback] = session.info.pop(
        AFTER_COMMIT_CALLBACKS_KEY, []
    )
    for callback in callbacks:
        try:
            await callback()
        except Exception:
            # `logger.exception` logs at error level with the traceback, so
            # Sentry will report it later. The message has no personal data.
            logger.exception("An after-commit callback failed after a commit")
