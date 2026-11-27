"""Unit tests for the engine, sessions and table base in `app/core/database.py`."""

import allure
from pydantic import SecretStr
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table
from sqlalchemy.schema import CreateTable

from app.core.database import (
    NAMING_CONVENTION,
    Base,
    build_async_database_url,
    create_database_engine,
    create_session_factory,
)

pytestmark = [allure.feature("server")]

EXAMPLE_DATABASE_URL = SecretStr(
    "postgresql://example_user:example_password"
    "@database.example.test:5432/example_database"
)


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
