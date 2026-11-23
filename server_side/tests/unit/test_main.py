"""Unit tests for the app factory in `app/main.py`."""

from collections.abc import Iterator

import allure
import pytest
from fastapi import FastAPI

import app.core.config as config_module
import app.main as main_module
from app.core.config import InvalidSettingsError, get_settings
from app.main import create_app

# Allure groups the results by feature. The app factory belongs to no feature.
pytestmark = [allure.feature("server")]


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """Empty the settings cache before and after each test.

    So each test reads the settings of its own environment.

    Yields:
        Nothing. The test runs between the setup and the clean-up.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_app_returns_app_with_title_when_settings_are_valid() -> None:
    # Arrange: tests/conftest.py has set APP_ENV.

    # Act
    created_app = create_app()

    # Assert
    assert isinstance(created_app, FastAPI)
    assert created_app.title == "Behördenbrief Assistant API"


def test_create_app_returns_new_app_when_called_twice() -> None:
    # Arrange: tests/conftest.py has set APP_ENV.

    # Act
    first_app = create_app()
    second_app = create_app()

    # Assert
    assert first_app is not second_app


def test_create_app_raises_invalid_settings_error_when_app_env_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: remove APP_ENV. `get_settings` must also skip the real `.env`
    # file, so we let it call `load_settings` without a file.
    monkeypatch.delenv("APP_ENV")
    original_load_settings = config_module.load_settings
    monkeypatch.setattr(
        config_module,
        "load_settings",
        lambda: original_load_settings(environment_file=None),
    )

    # Act
    with pytest.raises(InvalidSettingsError) as error_information:
        create_app()

    # Assert
    assert "APP_ENV" in str(error_information.value)


def test_main_module_exposes_app_when_imported() -> None:
    # Arrange: the module was imported at the top of this file.

    # Act
    module_app = main_module.app

    # Assert
    assert isinstance(module_app, FastAPI)
