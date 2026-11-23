"""Unit tests for the log formats and setup in `app/core/logging.py`."""

import json
import logging
import sys
from collections.abc import Iterator
from datetime import UTC, datetime

import allure
import pytest
from starlette.types import Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.logging import (
    APP_LOG_HANDLER_NAME,
    MASKED_DOWNLOAD_TOKEN,
    UVICORN_LOGGER_NAMES,
    DownloadTokenMaskingLogFilter,
    JsonLogFormatter,
    RequestIdLogFilter,
    RequestIdMiddleware,
    TextLogFormatter,
    configure_logging,
    current_request_id,
)

# An invented download token. Tests check that it never reaches a log line.
EXAMPLE_DOWNLOAD_TOKEN = "invented-download-token-123"  # noqa: S105  (test value)

# Allure groups the results by feature. Logging belongs to no single feature.
pytestmark = [allure.feature("server")]


@pytest.fixture(autouse=True)
def restore_logging_state() -> Iterator[None]:
    """Save the global logging state and put it back after each test.

    `configure_logging` changes the root logger and the Uvicorn loggers for
    the whole process. Without this, one test could change the next one.

    Yields:
        Nothing. The test runs between the setup and the clean-up.
    """
    # Save the root logger and the Uvicorn loggers.
    root_logger = logging.getLogger()
    saved_root_handlers = list(root_logger.handlers)
    saved_root_level = root_logger.level
    saved_uvicorn_states = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).propagate,
        )
        for name in UVICORN_LOGGER_NAMES
    }

    yield

    # Put everything back as it was.
    root_logger.handlers[:] = saved_root_handlers
    root_logger.setLevel(saved_root_level)
    for name, (handlers, propagate) in saved_uvicorn_states.items():
        logging.getLogger(name).handlers[:] = handlers
        logging.getLogger(name).propagate = propagate


def _make_log_record(
    message: str = "Letter is ready", **extra_fields: object
) -> logging.LogRecord:
    # A record like `logging.getLogger("app.test").info(message, extra=...)`.
    return logging.makeLogRecord(
        {
            "name": "app.test",
            "levelname": "INFO",
            "levelno": logging.INFO,
            "msg": message,
            **extra_fields,
        }
    )


def _make_log_record_with_exception() -> logging.LogRecord:
    # Raise and catch a real error, so the record has a real traceback.
    try:
        raise ValueError("Example error")
    except ValueError:
        return logging.makeLogRecord(
            {
                "name": "app.test",
                "levelname": "ERROR",
                "msg": "Failed",
                "exc_info": sys.exc_info(),
            }
        )


def _make_access_log_record(path: str) -> logging.LogRecord:
    # A record like the access line that Uvicorn writes for each request.
    return logging.makeLogRecord(
        {
            "name": "uvicorn.access",
            "levelname": "INFO",
            "levelno": logging.INFO,
            "msg": '%s - "%s %s HTTP/%s" %d',
            "args": ("127.0.0.1:50000", "GET", path, "1.1", 200),
        }
    )


async def _receive_nothing() -> Message:
    return {"type": "lifespan.startup"}


async def _send_nothing(message: Message) -> None:
    return None


def _get_app_handlers() -> list[logging.Handler]:
    return [
        handler
        for handler in logging.getLogger().handlers
        if handler.get_name() == APP_LOG_HANDLER_NAME
    ]


def test_json_log_formatter_returns_main_fields_when_record_is_given() -> None:
    # Arrange
    record = _make_log_record()

    # Act
    line = JsonLogFormatter().format(record)

    # Assert
    assert "\n" not in line
    log_entry = json.loads(line)
    assert log_entry["level"] == "INFO"
    assert log_entry["logger"] == "app.test"
    assert log_entry["message"] == "Letter is ready"
    assert "time" in log_entry


def test_json_log_formatter_writes_time_in_utc_when_record_is_given() -> None:
    # Arrange
    record = _make_log_record()

    # Act
    log_entry = json.loads(JsonLogFormatter().format(record))

    # Assert
    log_time = datetime.fromisoformat(log_entry["time"])
    assert log_time.utcoffset() == UTC.utcoffset(None)


def test_json_log_formatter_adds_extra_fields_when_record_has_extra_fields() -> None:
    # Arrange
    record = _make_log_record(message="Behördenbrief ready", letter_id=42)

    # Act
    line = JsonLogFormatter().format(record)

    # Assert: the extra field is there, and "ü" is not turned into "ü".
    assert json.loads(line)["letter_id"] == 42
    assert "Behördenbrief" in line


def test_json_log_formatter_keeps_main_fields_when_extra_field_has_same_name() -> None:
    # Arrange
    record = _make_log_record(level="not a real level")

    # Act
    log_entry = json.loads(JsonLogFormatter().format(record))

    # Assert
    assert log_entry["level"] == "INFO"


def test_json_log_formatter_skips_color_message_when_record_is_from_uvicorn() -> None:
    # Arrange
    record = _make_log_record(color_message="\x1b[32mStarted\x1b[0m")

    # Act
    log_entry = json.loads(JsonLogFormatter().format(record))

    # Assert
    assert "color_message" not in log_entry


def test_json_log_formatter_adds_exception_when_record_has_exception() -> None:
    # Arrange
    record = _make_log_record_with_exception()

    # Act
    log_entry = json.loads(JsonLogFormatter().format(record))

    # Assert
    assert "ValueError: Example error" in log_entry["exception"]


def test_text_log_formatter_writes_one_line_when_record_has_extra_fields() -> None:
    # Arrange
    record = _make_log_record(letter_id=42)

    # Act
    line = TextLogFormatter().format(record)

    # Assert
    assert line.endswith("INFO     app.test: Letter is ready  letter_id=42")
    assert " UTC " in line


def test_text_log_formatter_adds_exception_when_record_has_exception() -> None:
    # Arrange
    record = _make_log_record_with_exception()

    # Act
    line = TextLogFormatter().format(record)

    # Assert
    assert "ValueError: Example error" in line


def test_configure_logging_uses_json_formatter_when_app_env_is_production() -> None:
    # Arrange
    settings = Settings(app_env="production", log_level="INFO")

    # Act
    configure_logging(settings)

    # Assert
    assert isinstance(_get_app_handlers()[0].formatter, JsonLogFormatter)


def test_configure_logging_uses_text_formatter_when_app_env_is_development() -> None:
    # Arrange
    settings = Settings(app_env="development", log_level="INFO")

    # Act
    configure_logging(settings)

    # Assert
    assert isinstance(_get_app_handlers()[0].formatter, TextLogFormatter)


def test_configure_logging_sets_level_when_log_level_is_given() -> None:
    # Arrange
    settings = Settings(app_env="development", log_level="WARNING")

    # Act
    configure_logging(settings)

    # Assert: both the root logger and our handler use the level.
    assert logging.getLogger().level == logging.WARNING
    assert _get_app_handlers()[0].level == logging.WARNING


def test_configure_logging_keeps_one_app_handler_when_called_twice() -> None:
    # Arrange
    settings = Settings(app_env="development", log_level="INFO")

    # Act
    configure_logging(settings)
    configure_logging(settings)

    # Assert
    assert len(_get_app_handlers()) == 1


def test_configure_logging_keeps_other_handlers_when_called() -> None:
    # Arrange: a handler of another tool, like pytest's log capture.
    other_handler = logging.NullHandler()
    logging.getLogger().addHandler(other_handler)

    # Act
    configure_logging(Settings(app_env="development", log_level="INFO"))

    # Assert
    assert other_handler in logging.getLogger().handlers


def test_configure_logging_sends_uvicorn_lines_to_app_handler_when_called() -> None:
    # Arrange: Uvicorn starts with its own handler.
    logging.getLogger("uvicorn.access").addHandler(logging.NullHandler())
    logging.getLogger("uvicorn.access").propagate = False

    # Act
    configure_logging(Settings(app_env="development", log_level="INFO"))

    # Assert
    for name in UVICORN_LOGGER_NAMES:
        assert logging.getLogger(name).handlers == []
        assert logging.getLogger(name).propagate is True


def test_configure_logging_writes_json_line_to_stdout_when_app_env_is_production(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    configure_logging(Settings(app_env="production", log_level="INFO"))

    # Act
    logging.getLogger("app.test").info("Letter is ready", extra={"letter_id": 42})

    # Assert
    log_entry = json.loads(capsys.readouterr().out.strip())
    assert log_entry["message"] == "Letter is ready"
    assert log_entry["letter_id"] == 42


def test_configure_logging_hides_download_token_when_uvicorn_writes_access_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    configure_logging(Settings(app_env="production", log_level="INFO"))

    # Act: the same call that Uvicorn makes for each request.
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d',
        "127.0.0.1:50000",
        "GET",
        f"/api/v1/downloads/{EXAMPLE_DOWNLOAD_TOKEN}",
        "1.1",
        200,
    )

    # Assert
    output = capsys.readouterr().out
    assert EXAMPLE_DOWNLOAD_TOKEN not in output
    assert f"/api/v1/downloads/{MASKED_DOWNLOAD_TOKEN}" in output


def test_request_id_log_filter_adds_request_id_when_request_is_running() -> None:
    # Arrange
    record = _make_log_record()
    reset_token = current_request_id.set("example-request-id")

    # Act
    try:
        is_written = RequestIdLogFilter().filter(record)
    finally:
        current_request_id.reset(reset_token)

    # Assert
    assert is_written is True
    assert record.__dict__["request_id"] == "example-request-id"


def test_request_id_log_filter_adds_no_request_id_when_no_request_is_running() -> None:
    # Arrange: no request id is set.
    record = _make_log_record()

    # Act
    is_written = RequestIdLogFilter().filter(record)

    # Assert
    assert is_written is True
    assert "request_id" not in record.__dict__


@pytest.mark.parametrize(
    ("path", "expected_path"),
    [
        (
            f"/api/v1/downloads/{EXAMPLE_DOWNLOAD_TOKEN}",
            f"/api/v1/downloads/{MASKED_DOWNLOAD_TOKEN}",
        ),
        (
            f"/api/v1/downloads/{EXAMPLE_DOWNLOAD_TOKEN}?inline=1",
            f"/api/v1/downloads/{MASKED_DOWNLOAD_TOKEN}?inline=1",
        ),
    ],
)
def test_download_token_masking_log_filter_hides_token_when_path_is_download(
    path: str, expected_path: str
) -> None:
    # Arrange
    record = _make_access_log_record(path)

    # Act
    is_written = DownloadTokenMaskingLogFilter().filter(record)

    # Assert
    assert is_written is True
    assert EXAMPLE_DOWNLOAD_TOKEN not in record.getMessage()
    assert expected_path in record.getMessage()


def test_download_token_masking_log_filter_keeps_path_when_path_is_not_download() -> (
    None
):
    # Arrange
    record = _make_access_log_record("/health")

    # Act
    DownloadTokenMaskingLogFilter().filter(record)

    # Assert
    assert record.getMessage() == '127.0.0.1:50000 - "GET /health HTTP/1.1" 200'


def test_download_token_masking_log_filter_keeps_record_when_logger_is_not_access() -> (
    None
):
    # Arrange: an app line, not an access line, with values in `args`.
    record = _make_log_record(message="Path %s")
    record.args = ("/api/v1/downloads/x",)

    # Act
    DownloadTokenMaskingLogFilter().filter(record)

    # Assert
    assert record.args == ("/api/v1/downloads/x",)


async def test_request_id_middleware_sets_no_request_id_when_scope_is_lifespan() -> (
    None
):
    # Arrange: an inner app that remembers the request id it sees.
    seen_request_ids: list[str | None] = []

    async def inner_app(scope: Scope, receive: Receive, send: Send) -> None:
        seen_request_ids.append(current_request_id.get())

    middleware = RequestIdMiddleware(inner_app)

    # Act
    await middleware({"type": "lifespan"}, _receive_nothing, _send_nothing)

    # Assert
    assert seen_request_ids == [None]


async def test_request_id_middleware_removes_request_id_when_request_fails() -> None:
    # Arrange: an inner app that fails.
    async def failing_app(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("Example error")

    middleware = RequestIdMiddleware(failing_app)

    # Act
    with pytest.raises(RuntimeError):
        await middleware({"type": "http"}, _receive_nothing, _send_nothing)

    # Assert
    assert current_request_id.get() is None
