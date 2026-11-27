"""Unit tests for the shared dependencies in `app/core/dependencies.py`."""

import allure
import pytest
from fastapi import FastAPI, Request

from app.core.dependencies import get_database_session_factory

pytestmark = [allure.feature("server")]


def test_get_database_session_factory_raises_runtime_error_when_app_has_none() -> None:
    # Arrange: an app that was not built with `create_app`.
    request = Request({"type": "http", "app": FastAPI()})

    # Act
    with pytest.raises(RuntimeError) as error_information:
        get_database_session_factory(request)

    # Assert
    assert "no database session factory" in str(error_information.value)
