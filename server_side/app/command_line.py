"""Developer commands, for example make a user an admin or run the local MCP server.

Start them from `server_side/` (ARCHITECTURE §12.2):

    uv run python -m app.command_line                  # list all commands
    uv run python -m app.command_line <name> [options] # run one command

Each command is one `DeveloperCommand` in `DEVELOPER_COMMANDS`. Listing the
commands needs no settings, so it works without a `.env` file. A command that
needs the settings loads them itself.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

# The program name in the help text, so it shows the real way to start it.
PROGRAM_NAME = "python -m app.command_line"


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


# All real commands. Later tasks add one entry each (first T-028).
DEVELOPER_COMMANDS: tuple[DeveloperCommand, ...] = ()


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
