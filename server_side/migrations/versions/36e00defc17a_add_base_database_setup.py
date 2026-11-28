"""Add the base database setup that every later table needs.

1. Enable the extension pgvector for the `vector` column type (DATA_MODEL §6).
2. Create the trigger function `set_updated_at()` (DATA_MODEL §1).
3. Remove the default Data API rights on new objects in `public` (MEMORY D-058).

Revision ID: 36e00defc17a
Revises:
Create Date: 2026-11-28 01:12:22.654863
"""

from collections.abc import Sequence

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "36e00defc17a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable pgvector, add `set_updated_at()` and close the default rights."""
    # Supabase keeps extensions in their own schema, not in `public`. A new
    # database such as the TestDB does not have this schema yet (DATA_MODEL §9).
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")

    # Each table with `updated_at` gets a trigger that calls this function on
    # every UPDATE, so no code can forget to set the time (DATA_MODEL §1).
    # `search_path = ''` and the full name `pg_catalog.now()`: an object with
    # the same name in another schema can never be used instead.
    op.execute(
        """
        CREATE FUNCTION public.set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = ''
        AS $$
        BEGIN
            NEW.updated_at = pg_catalog.now();
            RETURN NEW;
        END;
        $$
        """
    )

    # New tables, sequences and functions that `postgres` creates in `public`
    # get no rights for the Data API roles. This is a second lock next to the
    # revoke in each table migration (MEMORY D-058, DATA_MODEL §8). Postgres
    # needs one statement per object type.
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON TABLES FROM anon, authenticated, service_role"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON SEQUENCES FROM anon, authenticated, service_role"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE ALL ON FUNCTIONS FROM anon, authenticated, service_role"
    )


def downgrade() -> None:
    """Remove `set_updated_at()` and pgvector; keep the closed default rights.

    Exception to RULES §9 (MEMORY D-058): the default rights are not given
    back, because that would open every new table to the Data API roles again.
    """
    # The reverse order of the upgrade. If a later migration still uses the
    # function or a `vector` column, these commands fail. That is wanted: the
    # later migrations must be downgraded first.
    op.execute("DROP FUNCTION IF EXISTS public.set_updated_at()")
    op.execute("DROP EXTENSION IF EXISTS vector")

    # The schema `extensions` stays: in the development database, Supabase
    # keeps other extensions there (DATA_MODEL §9).
