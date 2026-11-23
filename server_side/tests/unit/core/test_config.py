"""Unit tests for reading the app settings in `app/core/config.py`."""

from collections.abc import Iterator
from pathlib import Path

import allure
import pytest

from app.core.config import (
    InvalidSettingsError,
    Settings,
    get_settings,
    load_settings,
)

# Allure groups the results by feature. Settings belong to no single feature.
pytestmark = [allure.feature("server")]

# The environment variables that these tests set and remove.
SETTING_NAMES = [
    "APP_ENV",
    "LOG_LEVEL",
    "FRONTEND_BASE_URL",
    "CORS_ALLOWED_ORIGINS",
    "MAX_UPLOAD_REQUEST_MB",
]

# An invented address for the required FRONTEND_BASE_URL.
EXAMPLE_FRONTEND_BASE_URL = "https://app.example.test"


@pytest.fixture(autouse=True)
def clean_settings_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Remove our settings from the environment and empty the settings cache.

    So the computer's own environment cannot change the test results.

    Args:
        monkeypatch: Changes the environment only for one test.

    Yields:
        Nothing. The test runs between the setup and the clean-up.
    """
    # Remove the real values of this computer. Each test sets only what it needs.
    for setting_name in SETTING_NAMES:
        monkeypatch.delenv(setting_name, raising=False)

    # `get_settings` keeps its first result. Empty the cache before and after
    # the test, so no test sees settings that another test has read.
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_load_settings_returns_values_when_environment_is_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", EXAMPLE_FRONTEND_BASE_URL)

    # Act
    settings = load_settings(environment_file=None)

    # Assert
    assert settings.app_env == "production"
    assert settings.log_level == "WARNING"
    assert str(settings.frontend_base_url) == f"{EXAMPLE_FRONTEND_BASE_URL}/"


def test_load_settings_uses_info_log_level_when_log_level_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", EXAMPLE_FRONTEND_BASE_URL)

    # Act
    settings = load_settings(environment_file=None)

    # Assert
    assert settings.log_level == "INFO"


def test_load_settings_uses_info_log_level_when_log_level_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", EXAMPLE_FRONTEND_BASE_URL)

    # Act
    settings = load_settings(environment_file=None)

    # Assert
    assert settings.log_level == "INFO"


def test_load_settings_raises_invalid_settings_error_when_app_env_is_missing() -> None:
    # Arrange: the fixture has removed APP_ENV.

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        load_settings(environment_file=None)

    # Assert
    assert "APP_ENV" in str(error_information.value)
    assert "required" in str(error_information.value)


def test_load_settings_raises_invalid_settings_error_when_app_env_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "")

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        load_settings(environment_file=None)

    # Assert
    assert "APP_ENV" in str(error_information.value)


def test_load_settings_raises_invalid_settings_error_when_app_env_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "staging")

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        load_settings(environment_file=None)

    # Assert
    assert "APP_ENV" in str(error_information.value)


def test_load_settings_hides_value_in_error_message_when_value_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: this stands for a secret value that must never be shown.
    value_to_hide = "do-not-show-this-value"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", value_to_hide)
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", EXAMPLE_FRONTEND_BASE_URL)

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        load_settings(environment_file=None)

    # Assert: neither our message nor the chained Pydantic error shows the value.
    assert "LOG_LEVEL" in str(error_information.value)
    assert value_to_hide not in str(error_information.value)
    assert value_to_hide not in str(error_information.value.__cause__)


def test_load_settings_reads_values_when_environment_file_exists(
    tmp_path: Path,
) -> None:
    # Arrange
    environment_file = tmp_path / ".env"
    environment_file.write_text(
        "APP_ENV=test\nLOG_LEVEL=DEBUG\n"
        f"FRONTEND_BASE_URL={EXAMPLE_FRONTEND_BASE_URL}\n"
        f"CORS_ALLOWED_ORIGINS={EXAMPLE_FRONTEND_BASE_URL}\n",
        encoding="utf-8",
    )

    # Act
    settings = load_settings(environment_file=environment_file)

    # Assert
    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"


def test_load_settings_prefers_environment_variable_when_file_has_same_setting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Arrange
    environment_file = tmp_path / ".env"
    environment_file.write_text("APP_ENV=test\n", encoding="utf-8")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", EXAMPLE_FRONTEND_BASE_URL)

    # Act
    settings = load_settings(environment_file=environment_file)

    # Assert
    assert settings.app_env == "production"


def test_get_settings_returns_same_object_when_called_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: set all values, so a local `.env` file cannot change the result.
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", EXAMPLE_FRONTEND_BASE_URL)

    # Act
    first_settings = get_settings()
    second_settings = get_settings()

    # Assert
    assert first_settings is second_settings
    assert first_settings.app_env == "test"


def test_load_settings_raises_invalid_settings_error_when_frontend_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: the fixture has removed FRONTEND_BASE_URL.
    monkeypatch.setenv("APP_ENV", "development")

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        load_settings(environment_file=None)

    # Assert
    assert "FRONTEND_BASE_URL" in str(error_information.value)
    assert "required" in str(error_information.value)


def test_load_settings_raises_invalid_settings_error_when_frontend_url_is_not_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_BASE_URL", "not a url")

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        load_settings(environment_file=None)

    # Assert
    assert "FRONTEND_BASE_URL" in str(error_information.value)


def test_load_settings_splits_cors_origins_when_value_has_commas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: spaces and an empty entry, as a person might type it.
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", " http://localhost:3000 , https://app.example.test,"
    )

    # Act
    settings = load_settings(environment_file=None)

    # Assert
    assert settings.cors_allowed_origins == (
        "http://localhost:3000",
        "https://app.example.test",
    )


def test_load_settings_uses_30_mb_upload_limit_when_limit_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", EXAMPLE_FRONTEND_BASE_URL)

    # Act
    settings = load_settings(environment_file=None)

    # Assert: the value of API_DESIGN §1.8.
    assert settings.max_upload_request_mb == 30


def test_load_settings_reads_upload_limit_when_limit_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("MAX_UPLOAD_REQUEST_MB", "5")

    # Act
    settings = load_settings(environment_file=None)

    # Assert
    assert settings.max_upload_request_mb == 5


@pytest.mark.parametrize("wrong_limit", ["0", "-1", "thirty"])
def test_load_settings_raises_invalid_settings_error_when_upload_limit_is_wrong(
    monkeypatch: pytest.MonkeyPatch, wrong_limit: str
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("MAX_UPLOAD_REQUEST_MB", wrong_limit)

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        load_settings(environment_file=None)

    # Assert
    assert "MAX_UPLOAD_REQUEST_MB" in str(error_information.value)


def test_settings_keeps_cors_origins_when_value_is_already_list() -> None:
    # Arrange and act: code that builds the settings directly, not from text.
    settings = Settings(
        app_env="test",
        frontend_base_url=EXAMPLE_FRONTEND_BASE_URL,
        cors_allowed_origins=["http://localhost:3000"],
    )

    # Assert
    assert settings.cors_allowed_origins == ("http://localhost:3000",)


def test_load_settings_raises_invalid_settings_error_when_cors_origins_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: the fixture has removed CORS_ALLOWED_ORIGINS.
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        load_settings(environment_file=None)

    # Assert
    assert "CORS_ALLOWED_ORIGINS" in str(error_information.value)
    assert "required" in str(error_information.value)


@pytest.mark.parametrize(
    "wrong_origins",
    [
        " , ",
        "*",
        "https://*.example.test",
        "https://app.example.test/",
        "https://app.example.test/path",
        "app.example.test",
        "ftp://app.example.test",
        "https://user@app.example.test",
        "http://localhost:3000,https://app.example.test?x=1",
    ],
)
def test_load_settings_raises_invalid_settings_error_when_cors_origin_is_wrong(
    monkeypatch: pytest.MonkeyPatch, wrong_origins: str
) -> None:
    # Arrange
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_BASE_URL", EXAMPLE_FRONTEND_BASE_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", wrong_origins)

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        load_settings(environment_file=None)

    # Assert: the message names the setting, but never shows the value.
    assert "CORS_ALLOWED_ORIGINS" in str(error_information.value)
    assert "app.example.test" not in str(error_information.value)
