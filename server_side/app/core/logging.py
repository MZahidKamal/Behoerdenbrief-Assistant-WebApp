"""Set up structured logging that never writes personal data.

In production every log line is one JSON object, so a log tool can search it.
Locally every line is readable text. Both formats have the time (UTC), the
level, the logger name, the message and the extra fields (RULES §8).

This module only formats lines. The code that writes a log line must never
pass personal data, letter content, tokens or keys (SECURITY §15).
"""

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import Settings

# Our handler on the root logger has this name. So `configure_logging` can find
# and replace only its own handler, never the handlers of other tools.
APP_LOG_HANDLER_NAME = "app_log_handler"

# Uvicorn writes start-up lines and one access line per request with these
# loggers. Their lines should look like all our other lines.
UVICORN_LOGGER_NAMES = ("uvicorn", "uvicorn.error", "uvicorn.access")

# Every log record has these attributes; anything else came from `extra=`.
# Uvicorn also adds `color_message` (the message with terminal colours),
# which is only noise in our logs, so we skip it too.
_NOT_EXTRA_FIELDS = frozenset(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "color_message",
}


def _get_extra_fields(record: logging.LogRecord) -> dict[str, object]:
    return {
        field_name: value
        for field_name, value in vars(record).items()
        if field_name not in _NOT_EXTRA_FIELDS
    }


def _get_utc_time(record: logging.LogRecord) -> datetime:
    return datetime.fromtimestamp(record.created, tz=UTC)


class JsonLogFormatter(logging.Formatter):
    """Write each log record as one line of JSON (used in production)."""

    def format(self, record: logging.LogRecord) -> str:
        """Turn one log record into one JSON line.

        Args:
            record: The log record from Python's logging module.

        Returns:
            One JSON object with `time`, `level`, `logger`, `message`, the extra
            fields and, after an error, `exception`.
        """
        # The four fields that every line has.
        log_entry: dict[str, object] = {
            "time": _get_utc_time(record).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add the structured fields from `extra=` (RULES §8). They never
        # replace the four main fields.
        for field_name, value in _get_extra_fields(record).items():
            log_entry.setdefault(field_name, value)

        # After an error, add the traceback, so we can find the broken line.
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # `ensure_ascii=False` keeps "ü" readable. `default=str` turns values
        # like a UUID into text instead of failing.
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class TextLogFormatter(logging.Formatter):
    """Write each log record as one readable line (used locally and in tests)."""

    def format(self, record: logging.LogRecord) -> str:
        """Turn one log record into one readable line.

        Args:
            record: The log record from Python's logging module.

        Returns:
            For example `2026-11-23 10:15:30 UTC  INFO     app.main: Started
            letter_id=42`, and after an error the traceback on the next lines.
        """
        # Time, level, logger and message. The level has a fixed width, so the
        # columns line up and the lines are easy to scan.
        time_text = _get_utc_time(record).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = (
            f"{time_text}  {record.levelname:<8} {record.name}: {record.getMessage()}"
        )

        # Add the extra fields as `key=value` at the end of the line.
        extra_fields = _get_extra_fields(record)
        if extra_fields:
            field_texts = [f"{name}={value}" for name, value in extra_fields.items()]
            line += "  " + " ".join(field_texts)

        # After an error, add the traceback on the next lines.
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line


def configure_logging(settings: Settings) -> None:
    """Send all log lines to standard output in the right format.

    It is safe to call this function more than once: it replaces only its own
    handler and keeps the handlers of other tools (for example pytest).

    Args:
        settings: `APP_ENV` chooses the format (JSON only in production);
            `LOG_LEVEL` chooses the lowest level that is written.
    """
    # Choose the format. Render collects everything from standard output.
    # The level is also set on the handler, so lines that other loggers
    # (like Uvicorn) pass up to us follow LOG_LEVEL too.
    formatter: logging.Formatter
    if settings.app_env == "production":
        formatter = JsonLogFormatter()
    else:
        formatter = TextLogFormatter()
    app_handler = logging.StreamHandler(sys.stdout)
    app_handler.set_name(APP_LOG_HANDLER_NAME)
    app_handler.setFormatter(formatter)
    app_handler.setLevel(settings.log_level)

    # Remove our handler from an earlier call, so no line is written twice.
    root_logger = logging.getLogger()
    for existing_handler in list(root_logger.handlers):
        if existing_handler.get_name() == APP_LOG_HANDLER_NAME:
            root_logger.removeHandler(existing_handler)
    root_logger.addHandler(app_handler)
    root_logger.setLevel(settings.log_level)

    # Uvicorn has its own handlers with its own format. Remove them and pass
    # its lines up to our handler, so all lines have one format.
    for uvicorn_logger_name in UVICORN_LOGGER_NAMES:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
