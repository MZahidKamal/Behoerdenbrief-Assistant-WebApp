"""Read the app settings from environment variables.

Every part of the app reads its settings only through this module (RULES §4.1).
The values come from environment variables or from the local `server_side/.env`
file (ARCHITECTURE §11). Values are never written in the code.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import HttpUrl, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

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
