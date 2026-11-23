"""Unit tests for the developer command entry point in `app/command_line.py`."""

import argparse
import json
import runpy
import sys
from pathlib import Path

import allure
import pytest

import app.main
from app.command_line import (
    DEFAULT_OPENAPI_OUTPUT_PATH,
    DEVELOPER_COMMANDS,
    DeveloperCommand,
    main,
)
from app.core.config import InvalidSettingsError

# Allure groups the results by feature. The commands belong to no feature.
pytestmark = [allure.feature("server")]


def _add_greeting_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", required=True)


def _make_greeting_command(received_names: list[str]) -> DeveloperCommand:
    # An invented command that remembers the `--name` it got.
    def run_greeting(parsed_arguments: argparse.Namespace) -> int:
        received_names.append(parsed_arguments.name)
        return 0

    return DeveloperCommand(
        name="say_example_greeting",
        description="Say an example greeting.",
        add_arguments=_add_greeting_arguments,
        run=run_greeting,
    )


def _make_failing_command() -> DeveloperCommand:
    # An invented command that reports a failure with exit code 1.
    return DeveloperCommand(
        name="fail_on_purpose",
        description="Fail on purpose.",
        add_arguments=lambda parser: None,
        run=lambda parsed_arguments: 1,
    )


def test_main_lists_commands_and_returns_0_when_no_command_is_given(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    commands = [_make_greeting_command([]), _make_failing_command()]

    # Act
    exit_code = main([], commands)

    # Assert: every command with its description is in the list.
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "say_example_greeting" in output
    assert "Say an example greeting." in output
    assert "fail_on_purpose" in output


def test_main_runs_command_with_its_option_when_name_is_given() -> None:
    # Arrange
    received_names: list[str] = []
    commands = [_make_greeting_command(received_names)]

    # Act
    exit_code = main(["say_example_greeting", "--name", "Example"], commands)

    # Assert
    assert exit_code == 0
    assert received_names == ["Example"]


def test_main_returns_command_exit_code_when_command_fails() -> None:
    # Arrange
    commands = [_make_failing_command()]

    # Act
    exit_code = main(["fail_on_purpose"], commands)

    # Assert
    assert exit_code == 1


def test_main_stops_with_exit_code_2_when_command_is_unknown(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    commands = [_make_greeting_command([])]

    # Act
    with pytest.raises(SystemExit) as system_exit:
        main(["does_not_exist"], commands)

    # Assert: argparse names the valid commands.
    assert system_exit.value.code == 2
    assert "say_example_greeting" in capsys.readouterr().err


def test_main_stops_with_exit_code_2_when_required_option_is_missing() -> None:
    # Arrange
    commands = [_make_greeting_command([])]

    # Act
    with pytest.raises(SystemExit) as system_exit:
        main(["say_example_greeting"], commands)

    # Assert
    assert system_exit.value.code == 2


def test_main_says_no_commands_yet_when_list_is_empty(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange: no commands at all.

    # Act
    exit_code = main([], [])

    # Assert
    assert exit_code == 0
    assert "No commands yet." in capsys.readouterr().out


def test_developer_commands_have_unique_snake_case_names_when_list_is_read() -> None:
    # Arrange
    names = [command.name for command in DEVELOPER_COMMANDS]

    # Act and assert: names are unique and in snake_case (ARCHITECTURE §12.2).
    assert len(names) == len(set(names))
    assert all(name == name.lower() and " " not in name for name in names)


def test_module_lists_commands_when_started_with_python_m(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange: the same as `python -m app.command_line` without a command.
    # This file has already imported the module; `runpy` must load it fresh,
    # so it is removed for this test only (monkeypatch puts it back).
    monkeypatch.setattr(sys, "argv", ["app.command_line"])
    monkeypatch.delitem(sys.modules, "app.command_line")

    # Act: run the module as the main program, inside this test.
    with pytest.raises(SystemExit) as system_exit:
        runpy.run_module("app.command_line", run_name="__main__")

    # Assert
    assert system_exit.value.code == 0
    assert "python -m app.command_line" in capsys.readouterr().out


def test_main_lists_export_openapi_schema_when_no_command_is_given(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange: the real list of commands.

    # Act
    exit_code = main([])

    # Assert
    assert exit_code == 0
    assert "export_openapi_schema" in capsys.readouterr().out


def test_export_openapi_schema_writes_openapi_document_when_output_is_given(
    tmp_path: Path,
) -> None:
    # Arrange: a file in a new folder, so the folder is created too.
    output_path = tmp_path / "api" / "openapi.json"

    # Act
    exit_code = main(["export_openapi_schema", "--output", str(output_path)])

    # Assert: a valid OpenAPI document of our app.
    openapi_document = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert openapi_document["openapi"].startswith("3.")
    assert openapi_document["info"]["title"] == "Behördenbrief Assistant API"
    assert "/health" in openapi_document["paths"]


def test_export_openapi_schema_writes_only_newline_endings_when_file_is_written(
    tmp_path: Path,
) -> None:
    # Arrange
    output_path = tmp_path / "openapi.json"

    # Act
    main(["export_openapi_schema", "--output", str(output_path)])

    # Assert: "\n" only, also on Windows, and one at the end; "ö" stays as is.
    file_bytes = output_path.read_bytes()
    assert b"\r\n" not in file_bytes
    assert file_bytes.endswith(b"}\n")
    assert "Behördenbrief".encode() in file_bytes


def test_export_openapi_schema_uses_client_side_path_when_output_is_missing() -> None:
    # Arrange and act: the default value of the option.
    default_path_parts = DEFAULT_OPENAPI_OUTPUT_PATH.parts[-4:]

    # Assert (RULES §5).
    assert default_path_parts == ("client_side", "lib", "api", "openapi.json")


def test_export_openapi_schema_returns_1_with_message_when_settings_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange: the app cannot read its settings.
    def raise_invalid_settings_error() -> None:
        raise InvalidSettingsError("Missing or invalid settings: APP_ENV (required).")

    monkeypatch.setattr(app.main, "get_settings", raise_invalid_settings_error)
    output_path = tmp_path / "openapi.json"

    # Act
    exit_code = main(["export_openapi_schema", "--output", str(output_path)])

    # Assert: a short message, no file.
    assert exit_code == 1
    assert "APP_ENV" in capsys.readouterr().err
    assert not output_path.exists()
