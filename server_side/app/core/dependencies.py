"""Shared FastAPI dependencies: the database session (later also the current user).

Routes declare what they need with these types, and FastAPI provides it
(RULES §4.1, §4.2).
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def get_database_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """Return the session factory that `create_app` stored in the app state.

    Args:
        request: The current request; it knows its app.

    Returns:
        The session factory.

    Raises:
        RuntimeError: The app was not built with `create_app`.
    """
    # `app.state` has no types, and the value may be missing, so we check it
    # before we use it.
    session_factory = getattr(request.app.state, "database_session_factory", None)
    if not isinstance(session_factory, async_sessionmaker):
        raise RuntimeError("the app has no database session factory")
    return session_factory


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Give the route one session and one transaction (RULES §4.2).

    The work is committed when the route ends without an error. Any error
    rolls everything back and is raised again, so the error handlers still
    answer with the right Problem Details.

    Args:
        request: The current request.

    Yields:
        The session for this request.
    """
    session_factory = get_database_session_factory(request)
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            # Undo every change of this request, then let the error continue.
            await session.rollback()
            raise
        # Commit here, before the answer is sent (`scope="function"` below).
        # If the commit fails, the user gets a 500 and never a false success.
        await session.commit()


# Routes use only this type, so the scope is never forgotten. With the default
# scope, the commit would run after the answer is sent (MEMORY D-056).
DatabaseSession = Annotated[
    AsyncSession, Depends(get_database_session, scope="function")
]
