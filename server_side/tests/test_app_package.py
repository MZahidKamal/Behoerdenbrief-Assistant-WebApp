"""Tests for the `app` package itself."""

import importlib

import allure

# Allure groups the results by feature. This test belongs to no single feature.
pytestmark = [allure.feature("server")]


def test_import_app_returns_package_with_docstring_when_imported() -> None:
    # Arrange
    package_name = "app"

    # Act
    app_package = importlib.import_module(package_name)

    # Assert
    assert app_package.__doc__ is not None
    assert app_package.__doc__.strip() != ""
