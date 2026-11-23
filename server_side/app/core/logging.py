"""Set up structured logging that never writes personal data.

In production every log line is one JSON object, so a log tool can search it.
Locally every line is readable text. Both formats have the time (UTC), the
level, the logger name, the message and the extra fields (RULES §8).

A middleware gives every request its own request id. A log filter adds this
id to every line that is written during the request, so we can find all lines
of one request (RULES §8). Another filter hides the token in download paths
in the access log (SECURITY §15).

This module does not check the messages themselves. The code that writes a
log line must never pass personal data, letter content, tokens or keys.
"""

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import Settings

# Our handler on the root logger has this name. So `configure_logging` can find
# and replace only its own handler, never the handlers of other tools.
APP_LOG_HANDLER_NAME = "app_log_handler"

# Uvicorn writes start-up lines and one access line per request with these
# loggers. Their lines should look like all our other lines.
UVICORN_LOGGER_NAMES = ("uvicorn", "uvicorn.error", "uvicorn.access")

# The id of the request that is running now, or None outside a request.
# A context variable is like a global variable, but each request has its own
# value. So two requests at the same time never see each other's id.
current_request_id: ContextVar[str | None] = ContextVar(
    "current_request_id", default=None
)

# A download token works like a password for one file. So it must never be in
# the access log (SECURITY §15, API_DESIGN `GET /api/v1/downloads/{token}`).
# The pattern finds the token: everything after `/downloads/` up to the next
# `/`, `?`, `#` or space.
_DOWNLOAD_TOKEN_PATTERN = re.compile(r"(/api/v1/downloads/)[^/?#\s]+")
MASKED_DOWNLOAD_TOKEN = "***"  # noqa: S105  (a placeholder, not a password)

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


def _get_message(record: logging.LogRecord) -> str:
    # Some messages end with a newline, for example Uvicorn's
    # "Exception in ASGI application\n". Without it, the extra fields
    # (like `request_id`) stay on the same line as the message.
    return record.getMessage().rstrip()


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
            "message": _get_message(record),
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
            f"{time_text}  {record.levelname:<8} {record.name}: {_get_message(record)}"
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


class RequestIdMiddleware:
    """Give every HTTP and WebSocket request its own new request id.

    The id is a random UUID in hex form (32 characters). We never take an id
    from the client's `X-Request-ID` header: a client could send fake or very
    long text, and it would go straight into our logs.

    This is a plain ASGI middleware (not Starlette's `BaseHTTPMiddleware`).
    The route then runs in the same context, so it sees the id. The access line
    of Uvicorn is written while the response starts, so it sees the id too.
    After an unexpected error the id stays set, so the `500` answer, its access
    line and Uvicorn's traceback line also have it.

    Args:
        app: The next part of the app that handles the request.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Run one request with a new request id.

        Args:
            scope: Information about the connection, for example its type.
            receive: Reads the next message from the client.
            send: Sends the next message to the client.
        """
        # Start-up and shut-down ("lifespan") are not requests, so they get
        # no id.
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Set a new id for this request.
        reset_token = current_request_id.set(uuid4().hex)
        await self.app(scope, receive, send)

        # After a normal end, remove the id, so no id is left over. After an
        # error we keep it on purpose: Starlette's error layer (outside this
        # middleware) and Uvicorn's traceback line run after us, and they need
        # the id too. It is safe, because Uvicorn runs every request in its
        # own task, and the id lives only in that task. The next request
        # always sets a new id.
        current_request_id.reset(reset_token)


class RequestIdLogFilter(logging.Filter):
    """Add the current request id to each log record as `request_id`.

    Outside a request (for example at start-up) the record gets no
    `request_id` field.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add `request_id` to the record when a request is running.

        Args:
            record: The log record from Python's logging module.

        Returns:
            Always True, so the line is still written.
        """
        # The formatters write every extra attribute of the record as a field.
        # We use `__dict__`, because `LogRecord` has no typed `request_id`.
        request_id = current_request_id.get()
        if request_id is not None:
            record.__dict__["request_id"] = request_id
        return True


class DownloadTokenMaskingLogFilter(logging.Filter):
    """Replace the download token in Uvicorn's access lines with `***`."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Hide the token in `/api/v1/downloads/{download_token}` paths.

        Args:
            record: The log record from Python's logging module.

        Returns:
            Always True, so the line is still written, but without the token.
        """
        # Uvicorn writes the path as one of the values in `record.args`, not in
        # the message text. We check every text value, so the token is hidden
        # even if Uvicorn changes the order of the values (SECURITY §15).
        if record.name == "uvicorn.access" and isinstance(record.args, tuple):
            record.args = tuple(
                _mask_download_token(value) if isinstance(value, str) else value
                for value in record.args
            )
        return True


def _mask_download_token(text: str) -> str:
    return _DOWNLOAD_TOKEN_PATTERN.sub(rf"\g<1>{MASKED_DOWNLOAD_TOKEN}", text)


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

    # Filters on our handler see every line, also the lines that other
    # loggers pass up to us: add the request id and hide download tokens.
    app_handler.addFilter(RequestIdLogFilter())
    app_handler.addFilter(DownloadTokenMaskingLogFilter())

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
