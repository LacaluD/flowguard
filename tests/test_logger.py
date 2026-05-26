import logging
from pathlib import Path

import pytest

from src import logger as logger_module


def _raise_value_error() -> None:
    raise ValueError("boom")


def test_format_exception_short_without_traceback() -> None:
    exc = Exception("plain")

    result = logger_module.format_exception_short(exc)

    assert result == "Exception: plain"


def test_format_exception_short_with_traceback_contains_exception_name() -> None:
    try:
        _raise_value_error()
    except ValueError as exc:
        result = logger_module.format_exception_short(exc, limit=1)

    assert "ValueError: boom" in result
    assert "in _raise_value_error" in result


def test_log_exception_short_uses_requested_level(caplog: pytest.LogCaptureFixture) -> None:
    test_logger = logging.getLogger("test.log_exception_short.level")

    try:
        _raise_value_error()
    except ValueError as exc:
        with caplog.at_level(logging.WARNING, logger=test_logger.name):
            logger_module.log_exception_short(
                test_logger, exc, prefix="prefix", level="warning", limit=1)

    assert "prefix:" in caplog.text
    assert "ValueError: boom" in caplog.text


def test_log_exception_short_falls_back_to_error_for_unknown_level(caplog: pytest.LogCaptureFixture) -> None:
    test_logger = logging.getLogger("test.log_exception_short.fallback")

    try:
        _raise_value_error()
    except ValueError as exc:
        with caplog.at_level(logging.ERROR, logger=test_logger.name):
            logger_module.log_exception_short(
                test_logger, exc, prefix="prefix", level="unknown-level", limit=1)

    assert "prefix:" in caplog.text
    assert "ValueError: boom" in caplog.text


def test_resolve_level_valid_name_returns_expected_level() -> None:
    level, warning = logger_module._resolve_level("warning")

    assert level == logging.WARNING
    assert warning is None


def test_resolve_level_invalid_name_returns_fallback_and_warning() -> None:
    level, warning = logger_module._resolve_level(
        "bad-level", fallback=logging.INFO)

    assert level == logging.INFO
    assert warning is not None
    assert "Invalid log level" in warning


def test_get_settings_reads_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FILE_LEVEL", "ERROR")
    monkeypatch.setenv("EXTERNAL_LOG_LEVEL", "WARNING")

    settings = logger_module.get_settings()

    assert settings.log_level == "DEBUG"
    assert settings.log_file_level == "ERROR"
    assert settings.external_log_level == "WARNING"


def test_resolve_log_paths_uses_env_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "custom-logs"))
    monkeypatch.setenv("LOG_FILE_NAME", "validator.log")

    log_dir, log_file = logger_module._resolve_log_paths()

    assert log_dir == tmp_path / "custom-logs"
    assert log_file == tmp_path / "custom-logs" / "validator.log"


def test_ensure_log_path_exists_creates_dir_and_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOG_FILE_NAME", "main.log")

    main_logger = logger_module.MainLogger("test.ensure_log_path_exists")
    main_logger.ensure_log_path_exists()

    assert main_logger.log_dir_path.exists()
    assert main_logger.log_file_path.exists()


def test_configure_stdlib_logging_sets_external_levels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXTERNAL_LOG_LEVEL", "ERROR")

    main_logger = logger_module.MainLogger("test.configure_stdlib")
    main_logger.configure_stdlib_logging()

    assert logging.getLogger("aiohttp").level == logging.ERROR
    assert logging.getLogger("telethon").level == logging.ERROR


def test_resolve_file_log_level_returns_warning_for_invalid_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_FILE_LEVEL", "invalid")

    main_logger = logger_module.MainLogger("test.resolve_file_log_level")
    level_name, warning = main_logger.resolve_file_log_level()

    assert level_name == "invalid"
    assert warning is not None


def test_init_logger_configures_handlers_and_is_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOG_FILE_NAME", "main.log")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FILE_LEVEL", "INFO")
    logger_module.MainLogger._configured = False

    main_logger = logger_module.MainLogger("test.init_logger")
    configured_once = main_logger.init_logger()
    configured_twice = main_logger.init_logger()

    root_logger = logging.getLogger()

    assert configured_once is configured_twice
    assert logger_module.MainLogger._configured is True
    assert len(root_logger.handlers) == 3
    assert any(
        isinstance(h, logging.StreamHandler) and getattr(
            h, "stream", None) is logger_module.sys.stderr
        for h in root_logger.handlers
    )
    assert any(
        isinstance(h, logging.StreamHandler) and getattr(
            h, "stream", None) is logger_module.sys.stdout
        for h in root_logger.handlers
    )
    assert any(isinstance(h, logger_module.TimedRotatingFileHandler)
               for h in root_logger.handlers)


def test_init_logger_quiet_mode_reduces_console_noise(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOG_FILE_NAME", "main.log")
    logger_module.MainLogger._configured = False

    main_logger = logger_module.MainLogger("test.init_logger.quiet")
    main_logger.init_logger(quiet=True)

    root_logger = logging.getLogger()
    stderr_handlers = [
        h for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is logger_module.sys.stderr
    ]
    stdout_handlers = [
        h for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is logger_module.sys.stdout
    ]

    assert len(stderr_handlers) == 1
    assert len(stdout_handlers) == 1
    assert stderr_handlers[0].level == logging.ERROR
    assert stdout_handlers[0].level > logging.CRITICAL


def test_main_logger_wrapper_log_exception_short_logs_message(caplog: pytest.LogCaptureFixture) -> None:
    test_logger = logging.getLogger("test.main_logger.wrapper")
    main_logger = logger_module.MainLogger("test.main_logger.wrapper")
    main_logger.log = test_logger

    try:
        _raise_value_error()
    except ValueError as exc:
        with caplog.at_level(logging.ERROR, logger=test_logger.name):
            main_logger.log_exception_short(
                exc, prefix="wrapper", level="error", limit=1)

    assert "wrapper:" in caplog.text
    assert "ValueError: boom" in caplog.text


def test_main_logger_wrapper_format_exception_short_returns_text() -> None:
    main_logger = logger_module.MainLogger("test.main_logger.wrapper_format")

    result = main_logger.format_exception_short(Exception("wrapped"), limit=1)

    assert result == "Exception: wrapped"
