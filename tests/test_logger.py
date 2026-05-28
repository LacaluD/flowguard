import logging
import sys
import types
import importlib.util
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


def test_log_exception_short_uses_requested_level(
    caplog: pytest.LogCaptureFixture,
) -> None:
    test_logger = logging.getLogger("test.log_exception_short.level")

    try:
        _raise_value_error()
    except ValueError as exc:
        with caplog.at_level(logging.WARNING, logger=test_logger.name):
            logger_module.log_exception_short(
                test_logger, exc, prefix="prefix", level="warning", limit=1
            )

    assert "prefix:" in caplog.text
    assert "ValueError: boom" in caplog.text


def test_log_exception_short_falls_back_to_error_for_unknown_level(
    caplog: pytest.LogCaptureFixture,
) -> None:
    test_logger = logging.getLogger("test.log_exception_short.fallback")

    try:
        _raise_value_error()
    except ValueError as exc:
        with caplog.at_level(logging.ERROR, logger=test_logger.name):
            logger_module.log_exception_short(
                test_logger, exc, prefix="prefix", level="unknown-level", limit=1
            )

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


def test_resolve_log_paths_uses_env_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "custom-logs"))
    monkeypatch.setenv("LOG_FILE_NAME", "validator.log")

    log_dir, log_file = logger_module._resolve_log_paths()

    assert log_dir == tmp_path / "custom-logs"
    assert log_file == tmp_path / "custom-logs" / "validator.log"


def test_ensure_log_path_exists_creates_dir_and_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOG_FILE_NAME", "main.log")

    main_logger = logger_module.MainLogger("test.ensure_log_path_exists")
    main_logger.ensure_log_path_exists()

    assert main_logger.log_dir_path.exists()
    assert main_logger.log_file_path.exists()


def test_configure_stdlib_logging_sets_external_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXTERNAL_LOG_LEVEL", "ERROR")

    main_logger = logger_module.MainLogger("test.configure_stdlib")
    main_logger.configure_stdlib_logging()

    assert logging.getLogger("aiohttp").level == logging.ERROR
    assert logging.getLogger("telethon").level == logging.ERROR


def test_resolve_file_log_level_returns_warning_for_invalid_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_FILE_LEVEL", "invalid")

    main_logger = logger_module.MainLogger("test.resolve_file_log_level")
    level_name, warning = main_logger.resolve_file_log_level()

    assert level_name == "invalid"
    assert warning is not None


def test_init_logger_configures_loguru_sinks_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOG_FILE_NAME", "main.log")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FILE_LEVEL", "INFO")
    logger_module.MainLogger._configured = False

    add_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    remove_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_add(*args: object, **kwargs: object) -> int:
        add_calls.append((args, kwargs))
        return len(add_calls)

    def fake_remove(*args: object, **kwargs: object) -> None:
        remove_calls.append((args, kwargs))

    monkeypatch.setattr(logger_module.LOGURU_LOGGER, "add", fake_add)
    monkeypatch.setattr(logger_module.LOGURU_LOGGER, "remove", fake_remove)

    main_logger = logger_module.MainLogger("test.init_logger")
    configured_once = main_logger.init_logger()
    configured_twice = main_logger.init_logger()

    assert configured_once is configured_twice
    assert logger_module.MainLogger._configured is True
    assert len(remove_calls) == 1
    assert len(add_calls) == 3
    assert add_calls[0][0][0] is logger_module.sys.stderr
    assert add_calls[0][1]["level"] == "WARNING"
    assert add_calls[1][0][0] is logger_module.sys.stdout
    assert add_calls[1][1]["level"] == "DEBUG"
    assert callable(add_calls[1][1]["filter"])
    assert add_calls[2][0][0] == str(main_logger.log_file_path)
    assert add_calls[2][1]["level"] == "INFO"


def test_init_logger_quiet_mode_reduces_console_noise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOG_FILE_NAME", "main.log")
    logger_module.MainLogger._configured = False

    add_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_add(*args: object, **kwargs: object) -> int:
        add_calls.append((args, kwargs))
        return len(add_calls)

    monkeypatch.setattr(logger_module.LOGURU_LOGGER, "add", fake_add)
    monkeypatch.setattr(logger_module.LOGURU_LOGGER,
                        "remove", lambda *a, **k: None)

    main_logger = logger_module.MainLogger("test.init_logger.quiet")
    main_logger.init_logger(quiet=True)
    assert len(add_calls) == 3
    assert add_calls[0][0][0] is logger_module.sys.stderr
    assert add_calls[0][1]["level"] == "ERROR"
    assert add_calls[1][0][0] is logger_module.sys.stdout
    assert add_calls[1][1]["level"] == "SUCCESS"


def test_main_logger_wrapper_log_exception_short_logs_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    test_logger = logging.getLogger("test.main_logger.wrapper")
    main_logger = logger_module.MainLogger("test.main_logger.wrapper")
    main_logger.log = test_logger

    try:
        _raise_value_error()
    except ValueError as exc:
        with caplog.at_level(logging.ERROR, logger=test_logger.name):
            main_logger.log_exception_short(
                exc, prefix="wrapper", level="error", limit=1
            )

    assert "wrapper:" in caplog.text
    assert "ValueError: boom" in caplog.text


def test_main_logger_wrapper_format_exception_short_returns_text() -> None:
    main_logger = logger_module.MainLogger("test.main_logger.wrapper_format")

    result = main_logger.format_exception_short(Exception("wrapped"), limit=1)

    assert result == "Exception: wrapped"


def test_format_exception_short_when_extracted_traceback_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    try:
        _raise_value_error()
    except ValueError as exc:
        monkeypatch.setattr(logger_module.traceback,
                            "extract_tb", lambda _tb: [])
        result = logger_module.format_exception_short(exc, limit=1)

    assert result == "ValueError: boom"


def test_format_exception_short_falls_back_to_absolute_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    try:
        _raise_value_error()
    except ValueError as exc:
        monkeypatch.setattr(logger_module.Path, "cwd",
                            lambda: Path("/__not_matching_cwd__"))
        result = logger_module.format_exception_short(exc, limit=1)

    assert "ValueError: boom" in result
    assert '"' in result


def test_level_no_to_name_handles_success_and_unknown() -> None:
    assert logger_module._level_no_to_name(logger_module.SUCCESS) == "SUCCESS"
    assert logger_module._level_no_to_name(12345) == "INFO"


def test_render_stdlib_message_falls_back_when_percent_format_invalid() -> None:
    rendered = logger_module._render_stdlib_message("value=%d", ("oops",))

    assert rendered == "value=%d oops"


def test_stdlib_like_loguru_adapter_methods_delegate_correctly() -> None:
    class FakeBoundLogger:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        def debug(self, text: str) -> None:
            self.calls.append(("debug", text))

        def info(self, text: str) -> None:
            self.calls.append(("info", text))

        def warning(self, text: str) -> None:
            self.calls.append(("warning", text))

        def error(self, text: str) -> None:
            self.calls.append(("error", text))

        def critical(self, text: str) -> None:
            self.calls.append(("critical", text))

        def success(self, text: str) -> None:
            self.calls.append(("success", text))

        def log(self, level: str, text: str) -> None:
            self.calls.append((f"log:{level}", text))

        def bind(self, **kwargs: object) -> "FakeBoundLogger":
            self.calls.append(("bind", kwargs))
            return self

        def opt(self, exception: bool = False) -> "FakeBoundLogger":
            self.calls.append(("opt", exception))
            return self

        def custom_method(self) -> str:
            return "ok"

    fake = FakeBoundLogger()
    adapter = logger_module.StdlibLikeLoguruAdapter(fake)

    adapter.warning("w=%s", "1")
    adapter.critical("c=%s", "2")
    adapter.success("s=%s", "3")
    adapter.exception("ex=%s", "4")
    adapter.log("info", "i=%s", "5")
    rebound = adapter.bind(extra="x")

    assert isinstance(rebound, logger_module.StdlibLikeLoguruAdapter)
    assert ("warning", "w=1") in fake.calls
    assert ("critical", "c=2") in fake.calls
    assert ("success", "s=3") in fake.calls
    assert ("opt", True) in fake.calls
    assert ("error", "ex=4") in fake.calls
    assert ("log:INFO", "i=5") in fake.calls
    assert adapter.custom_method() == "ok"


def test_init_logger_emits_invalid_level_warnings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOG_FILE_NAME", "main.log")
    monkeypatch.setenv("LOG_LEVEL", "bad-console")
    monkeypatch.setenv("LOG_FILE_LEVEL", "bad-file")
    logger_module.MainLogger._configured = False

    messages: list[str] = []
    monkeypatch.setattr(
        logger_module.StdlibLikeLoguruAdapter,
        "warning",
        lambda self, message, *args, **kwargs: messages.append(str(message)),
    )

    logger_module.MainLogger("test.invalid.levels").init_logger()

    assert len(messages) >= 2
    assert "Invalid log level 'bad-console'" in "\n".join(messages)
    assert "Invalid log level 'bad-file'" in "\n".join(messages)


def test_logger_module_import_executes_success_level_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    module_path = Path(__file__).resolve().parents[1] / "src" / "logger.py"

    class FakeLogger:
        def __init__(self) -> None:
            self.fallback_calls: list[tuple[str, dict[str, object]]] = []

        def patch(self, _func):
            return self

        def level(self, name: str, **kwargs):
            if name == "SUCCESS" and not kwargs:
                raise ValueError("missing")
            self.fallback_calls.append((name, kwargs))

    fake_logger = FakeLogger()
    fake_loguru = types.ModuleType("loguru")
    fake_loguru.logger = fake_logger  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "loguru", fake_loguru)

    spec = importlib.util.spec_from_file_location(
        "logger_cov_import_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert ("SUCCESS", {"no": 25, "color": "<green>"}
            ) in fake_logger.fallback_calls
