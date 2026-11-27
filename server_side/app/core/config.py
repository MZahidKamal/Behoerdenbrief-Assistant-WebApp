"""Read the app settings from environment variables.

Every part of the app reads its settings only through this module (RULES §4.1).
The values come from environment variables or from the local `server_side/.env`
file (ARCHITECTURE §11). Values are never written in the code.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, HttpUrl, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# The local `.env` file sits in `server_side/`, two folders above this file.
# We use a full path, so the file is found from any working directory.
DEFAULT_ENVIRONMENT_FILE = Path(__file__).resolve().parents[2] / ".env"


class InvalidSettingsError(Exception):
    """A setting is missing or has a wrong value.

    The app cannot start safely without correct settings, so this error stops it.
    The message names only the variables, never their values, because a value
    can be a secret (SECURITY §13).
    """


class Settings(BaseSettings):
    """All settings of the API and the worker.

    Each field reads the environment variable with the same name in upper case.
    For example, `app_env` reads `APP_ENV`.

    Attributes:
        app_env: Where the app runs: `development`, `test` or `production`.
            Required. There is no default, because a wrong guess is dangerous
            (for example, development features in production).
        log_level: The lowest level that is written to the logs. Optional,
            the default is `INFO`.
        frontend_base_url: The address of the web app, for example
            `http://localhost:3000`. Required, because a wrong default would
            send users to wrong links. Used for the `type` link of error
            responses (API_DESIGN §3.1), and later for Stripe and email links.
        cors_allowed_origins: The web addresses whose pages may call the API
            from a browser (SECURITY §12). Required. In the environment it is
            one text with commas, for example
            `http://localhost:3000,https://app.example`. Each entry is
            `http(s)://host[:port]`, without a path and without `*`.
        max_upload_request_mb: The largest request body in megabytes
            (1 MB = 1024 × 1024 bytes). Optional, the default is 30
            (API_DESIGN §1.8). Must be larger than 0.
        database_url: The connection string of the application database, for
            example `postgresql://user:password@host:5432/postgres`. Required.
            Locally it is the `postgres` database of the local Supabase
            (MEMORY D-039). Kept as a secret, because it holds the password.
        test_database_url: The connection string of the test database
            `behoerdenbrief_assistant_webapp_testdb` (ARCHITECTURE §11).
            Optional: only the automated tests use it, never the app.
    """

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        # An empty value (`APP_ENV=`) counts as missing. So a copied
        # `.env.example` with empty values gives a clear "missing" error.
        env_ignore_empty=True,
        # Other variables in the environment or in `.env` are not ours to check.
        extra="ignore",
        # Error messages must never show input values. Later settings hold
        # secrets such as encryption keys (SECURITY §13).
        hide_input_in_errors=True,
        # Settings never change while the app runs.
        frozen=True,
    )

    app_env: Literal["development", "test", "production"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    frontend_base_url: HttpUrl
    # `NoDecode`: pydantic-settings would read a list as JSON. We want a
    # simple text with commas instead, so the validator below splits it.
    cors_allowed_origins: Annotated[tuple[str, ...], NoDecode]
    max_upload_request_mb: int = Field(default=30, gt=0)
    # `SecretStr` shows `**********` when printed, so a log line or an error
    # can never show the database password (SECURITY §13).
    database_url: SecretStr
    test_database_url: SecretStr | None = None

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_cors_allowed_origins(cls, value: object) -> object:
        """Split the comma text into single origins.

        Args:
            value: The raw value, for example
                `"http://localhost:3000, https://app.example"`.

        Returns:
            The origins without spaces and without empty entries, or the value
            unchanged if it is not a text.
        """
        if isinstance(value, str):
            return tuple(
                origin.strip() for origin in value.split(",") if origin.strip()
            )
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def check_cors_allowed_origins(cls, origins: tuple[str, ...]) -> tuple[str, ...]:
        """Check that every origin is one exact web address.

        A browser sends its origin as `scheme://host[:port]`. Only an exact
        match gets permission, so a path or a `*` would be a mistake. A `*`
        would even allow every website (SECURITY §12: no wildcard).

        Args:
            origins: The split origins.

        Returns:
            The same origins.

        Raises:
            ValueError: The list is empty, or an origin has a wrong form. The
                message never shows the value.
        """
        # At least one frontend must be allowed, or the web app cannot work.
        if not origins:
            raise ValueError("at least one origin is required")

        # Each origin must be exactly `http(s)://host[:port]`.
        for origin in origins:
            parts = urlsplit(origin)
            has_only_scheme_and_host = (
                parts.scheme in ("http", "https")
                and parts.netloc != ""
                and "@" not in parts.netloc
                and "*" not in origin
                and parts.path == ""
                and parts.query == ""
                and parts.fragment == ""
            )
            if not has_only_scheme_and_host:
                raise ValueError(
                    "each origin must look like https://host or http://host:port, "
                    "without a path and without *"
                )
        return origins

    @field_validator("database_url", "test_database_url")
    @classmethod
    def check_database_url(cls, database_url: SecretStr | None) -> SecretStr | None:
        """Check that a database URL is a full Postgres connection string.

        We accept only the normal form `postgresql://...` that Supabase shows.
        `core/database.py` adds the async driver itself, so `.env` never needs
        to know which driver the code uses.

        Args:
            database_url: The URL as a secret, or `None` when it is not set.

        Returns:
            The same URL.

        Raises:
            ValueError: The URL has a wrong form. The message never shows the
                value, because it holds the password.
        """
        # An optional URL that is not set is fine.
        if database_url is None:
            return None

        # A host and a database name are needed, or the connection fails late
        # with an unclear error.
        parts = urlsplit(database_url.get_secret_value())
        has_postgres_form = (
            parts.scheme == "postgresql"
            and parts.hostname is not None
            and parts.path.strip("/") != ""
        )
        if not has_postgres_form:
            raise ValueError(
                "must look like postgresql://user:password@host:port/database_name"
            )
        return database_url


def load_settings(environment_file: Path | None = DEFAULT_ENVIRONMENT_FILE) -> Settings:
    """Read and check all settings.

    Environment variables win over values in the `.env` file.

    Args:
        environment_file: The `.env` file to read. A missing file is skipped.
            `None` reads only environment variables (used by tests).

    Returns:
        The checked settings.

    Raises:
        InvalidSettingsError: A required setting is missing, or a setting has
            a wrong value.
    """
    # Pydantic reads every setting and checks its type and allowed values.
    # If anything is wrong, it raises one ValidationError with all problems.
    try:
        return Settings(_env_file=environment_file)
    except ValidationError as error:
        # Build one short line per problem: the variable name and the reason.
        # We use only the field name and Pydantic's message, never the input.
        problems = [
            f"{str(problem['loc'][0]).upper()} ({problem['msg']})"
            for problem in error.errors()
        ]

        # Stop with one clear message that also says how to fix it.
        # `from error` keeps the Pydantic error for debugging; it has no values.
        message = (
            "Missing or invalid settings: "
            + "; ".join(problems)
            + ". Set them as environment variables or in server_side/.env "
            + "(see server_side/.env.example)."
        )
        raise InvalidSettingsError(message) from error


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the app settings, read only once.

    The first call reads and checks the settings. Later calls return the same
    object, so the environment is not read again for every request.

    Returns:
        The checked settings.

    Raises:
        InvalidSettingsError: A required setting is missing, or a setting has
            a wrong value.
    """
    return load_settings()
