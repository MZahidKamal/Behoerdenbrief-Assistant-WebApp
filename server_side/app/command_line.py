"""Developer commands, for example make a user an admin or run the local MCP server.

Start them from `server_side/` (ARCHITECTURE §12.2):

    uv run python -m app.command_line                  # list all commands
    uv run python -m app.command_line <name> [options] # run one command

Each command is one `DeveloperCommand` in `DEVELOPER_COMMANDS`. Listing the
commands needs no settings, so it works without a `.env` file. A command that
needs the settings loads them itself.
"""

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.core.config import InvalidSettingsError

# The program name in the help text, so it shows the real way to start it.
PROGRAM_NAME = "python -m app.command_line"

# The frontend generates its API types from this file (RULES §5). The path is
# found from this file's place (`server_side/app/`), so the command works from
# any working directory.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPENAPI_OUTPUT_PATH = (
    REPOSITORY_ROOT / "client_side" / "lib" / "api" / "openapi.json"
)


@dataclass(frozen=True)
class DeveloperCommand:
    """One developer command.

    Attributes:
        name: The name to type, in snake_case, for example
            `export_openapi_schema` (ARCHITECTURE §12.2).
        description: One short line for the list of commands.
        add_arguments: Adds the command's own options (for example
            `--email`) to its parser.
        run: Does the work with the read options. Returns the exit code:
            0 means success, any other number means failure.
    """

    name: str
    description: str
    add_arguments: Callable[[argparse.ArgumentParser], None]
    run: Callable[[argparse.Namespace], int]


def _add_export_openapi_schema_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OPENAPI_OUTPUT_PATH,
        help="Where to write the file. Default: client_side/lib/api/openapi.json",
    )


def export_openapi_schema(parsed_arguments: argparse.Namespace) -> int:
    """Write the OpenAPI document of the API to a file, without a server.

    The app is only built in memory and asked for its schema. The frontend
    turns the file into TypeScript types (RULES §5, ARCHITECTURE §12.2).

    Args:
        parsed_arguments: The read options; `output` is the file path.

    Returns:
        0 when the file is written, 1 when a setting is missing or wrong.
    """
    # Import here, not at the top: listing the commands must work without
    # settings, but building the app needs them.
    from app.main import create_app

    # Build the app. Without correct settings it cannot be built; show the
    # short message (it never contains values), not a long traceback.
    try:
        application = create_app()
    except InvalidSettingsError as error:
        print(f"Cannot build the app: {error}", file=sys.stderr)
        return 1

    # Write readable JSON. Always "\n" line endings, also on Windows, so a
    # check on Linux (CI) sees no difference. "ü" stays readable.
    output_path: Path = parsed_arguments.output
    openapi_document = json.dumps(application.openapi(), indent=2, ensure_ascii=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(openapi_document + "\n", encoding="utf-8", newline="\n")

    print(f"Wrote the OpenAPI document to {output_path}.")
    return 0


# All real commands. Later tasks add one entry each.
DEVELOPER_COMMANDS: tuple[DeveloperCommand, ...] = (
    DeveloperCommand(
        name="export_openapi_schema",
        description="Write the OpenAPI document to client_side/lib/api/openapi.json.",
        add_arguments=_add_export_openapi_schema_arguments,
        run=export_openapi_schema,
    ),
)


def build_argument_parser(
    commands: Sequence[DeveloperCommand],
) -> argparse.ArgumentParser:
    """Build the parser with one sub-command per developer command.

    Args:
        commands: The commands that can be run.

    Returns:
        A parser. After parsing, `command_name` holds the chosen name, or None
        when no name was given.
    """
    # The main parser. With no commands yet, the list says so clearly.
    command_list_text = (
        "Available commands are listed below." if commands else "No commands yet."
    )
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description=f"Developer commands of the backend. {command_list_text}",
    )

    # One sub-parser per command. argparse shows them in the help text and
    # refuses unknown names with a list of the valid ones.
    subparsers = parser.add_subparsers(
        dest="command_name", title="commands", metavar="<command>"
    )
    for command in commands:
        command_parser = subparsers.add_parser(
            command.name, help=command.description, description=command.description
        )
        command.add_arguments(command_parser)

    return parser


def main(
    arguments: Sequence[str] | None = None,
    commands: Sequence[DeveloperCommand] = DEVELOPER_COMMANDS,
) -> int:
    """Read the command line and run the chosen command.

    Args:
        arguments: The words after the program name. None reads them from
            `sys.argv` (the normal way). Tests pass their own list.
        commands: The commands that can be run. Tests pass their own.

    Returns:
        The exit code: 0 for success. An unknown command or a wrong option
        stops the program with exit code 2 (argparse does this).
    """
    parser = build_argument_parser(commands)
    parsed_arguments = parser.parse_args(arguments)

    # No command name: show the list of commands and the help.
    if parsed_arguments.command_name is None:
        parser.print_help()
        return 0

    # Run the chosen command. argparse has already checked that it exists.
    commands_by_name = {command.name: command for command in commands}
    chosen_command = commands_by_name[parsed_arguments.command_name]
    return chosen_command.run(parsed_arguments)


# Runs only with `python -m app.command_line`, not when another file imports it.
if __name__ == "__main__":
    sys.exit(main())
