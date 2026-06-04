"""Main logger module"""

import logging
import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Final, cast

from loguru import logger as _base_loguru_logger


def format_exception_short(exc: Exception, limit: int = 1) -> str:
    """Return short exception text with last traceback frames only."""
    tb = exc.__traceback__
    if not tb:
        return f"{type(exc).__name__}: {exc}"

    extracted = traceback.extract_tb(tb)
    if not extracted:
        return f"{type(exc).__name__}: {exc}"

    frames = extracted[-limit:] if limit <= len(extracted) else extracted

    frame_texts = []
    cwd = Path.cwd()
    for fr in frames:
        filename = fr.filename
        try:
            rel = Path(filename).relative_to(cwd)
            filename_display = str(Path("..") / rel)
        except Exception:
            filename_display = filename

        lineno = fr.lineno
        func = fr.name
        line = fr.line.strip() if fr.line else ""
        frame_texts.append(
            f'"{filename_display}", line {lineno}, in {func}\n    {line}'
        )

    return "\n".join(frame_texts) + f"\n{type(exc).__name__}: {exc}"


def log_exception_short(
    log: Any,
    exc: Exception,
    prefix: str = "",
    level: str = "error",
    limit: int = 1,
) -> None:
    """Log a compact exception message with optional traceback tail.

    Args:
        log: Standart library logger instance.
        exc: Exception instance to format.
        prefix: Optional text prefix shown before exception details.
        level: Log method name (e.g. "error", "warning", "info").
        limit: Number of traceback frames from the end to include.
    """
    try:
        body = format_exception_short(exc, limit=limit)
        text = f"{prefix}: {body}" if prefix else body

        log_method = getattr(log, level, None)
        if not log_method:
            log.error(text)
        else:
            log_method(text)
    except Exception as err:  # pragma: no cover - very defensive
        log.error(f"Failed to log exception short: {err}")


@dataclass(frozen=True)
class LoggerSettings:
    """Minimal logger settings loaded from environment variables."""

    log_level: str = "INFO"
    log_file_level: str = "INFO"
    external_log_level: str = "INFO"


def get_settings() -> LoggerSettings:
    """Return logger settings with sane defaults for this project."""
    return LoggerSettings(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file_level=os.getenv("LOG_FILE_LEVEL", "INFO"),
        external_log_level=os.getenv("EXTERNAL_LOG_LEVEL", "INFO"),
    )


def _resolve_log_paths() -> tuple[Path, Path]:
    """Resolve log directory/file from environment or defaults."""
    log_dir_path = Path(os.getenv("LOG_DIR", "logs"))
    log_file_name = os.getenv("LOG_FILE_NAME", "main.log")
    return log_dir_path, log_dir_path / log_file_name


LOGURU_FORMAT: Final[str] = (
    "<green>[{time:YYYY-MM-DD HH:mm:ss}]</green> "
    "<level>[{level: <8}]</level> "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - {message}"
)

SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")

LOGURU_LOGGER = _base_loguru_logger.patch(
    lambda record: record["extra"].setdefault("logger_name", record["name"])
)

try:
    LOGURU_LOGGER.level("SUCCESS")
except ValueError:
    LOGURU_LOGGER.level("SUCCESS", no=SUCCESS, color="<green>")


def _resolve_level(
    level_name: str, fallback: int = logging.INFO
) -> tuple[int, str | None]:
    """Resolve a string log level to stdlib int level with optional warning."""
    normalized = (level_name or "").strip().upper()
    if hasattr(logging, normalized):
        maybe_level = getattr(logging, normalized)
        if isinstance(maybe_level, int):
            return maybe_level, None

    warning_message = f"Invalid log level '{level_name}'. Fallback to {logging.getLevelName(fallback)} was applied."
    return fallback, warning_message


def _level_no_to_name(level_no: int) -> str:
    """Map stdlib level number to a loguru level name."""
    if level_no == SUCCESS:
        return "SUCCESS"

    level_name = logging.getLevelName(level_no)
    if isinstance(level_name, str) and level_name.isupper():
        return level_name

    return "INFO"


def _render_stdlib_message(message: Any, args: tuple[Any, ...]) -> str:
    """Render stdlib-style '%'-formatted messages for backward compatibility."""
    rendered = str(message)
    if not args:
        return rendered

    try:
        return rendered % args
    except Exception:
        fallback_args = " ".join(str(arg) for arg in args)
        return f"{rendered} {fallback_args}" if fallback_args else rendered


class StdlibLikeLoguruAdapter:
    """Adapter exposing stdlib-like logger methods over a bound loguru logger."""

    def __init__(self, bound_logger: Any):
        self._logger = bound_logger

    def debug(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(_render_stdlib_message(message, args))

    def info(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.info(_render_stdlib_message(message, args))

    def warning(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(_render_stdlib_message(message, args))

    def error(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.error(_render_stdlib_message(message, args))

    def critical(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.critical(_render_stdlib_message(message, args))

    def success(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.success(_render_stdlib_message(message, args))

    def exception(self, message: Any, *args: Any, **kwargs: Any) -> None:
        text = _render_stdlib_message(message, args)
        self._logger.opt(exception=True).error(text)

    def log(self, level: str, message: Any, *args: Any, **kwargs: Any) -> None:
        text = _render_stdlib_message(message, args)
        self._logger.log(str(level).upper(), text)

    def bind(self, **kwargs: Any) -> "StdlibLikeLoguruAdapter":
        return StdlibLikeLoguruAdapter(self._logger.bind(**kwargs))

    def __getattr__(self, name: str) -> Callable[..., Any]:
        return cast(Callable[..., Any], getattr(self._logger, name))


class MainLogger:
    """Main project logger"""

    _configured: bool = False

    def __init__(self, logger_name: str = "ymlvalidator"):
        self.logger_name = logger_name
        self._bound_logger = LOGURU_LOGGER.bind(logger_name=logger_name)
        self.logger = StdlibLikeLoguruAdapter(self._bound_logger)
        self.log = self.logger
        self.settings = get_settings()
        self.log_dir_path, self.log_file_path = _resolve_log_paths()

    def ensure_log_path_exists(self) -> None:
        """Get root path for logs dir and check if they are exists"""
        self.log_dir_path.mkdir(parents=True, exist_ok=True)
        self.log_file_path.touch(exist_ok=True)

    def resolve_file_log_level(self) -> tuple[str, str | None]:
        """Validate LOG_FILE_LEVEL and return safe value with optional warning text."""
        _, warning = _resolve_level(self.settings.log_file_level, fallback=logging.INFO)
        return self.settings.log_file_level, warning

    def configure_stdlib_logging(self) -> None:
        """Set external libraries logging level from EXTERNAL_LOG_LEVEL."""
        external_level, _ = _resolve_level(
            self.settings.external_log_level, fallback=logging.INFO
        )
        for external_logger_name in ("aiohttp", "telethon"):
            logging.getLogger(external_logger_name).setLevel(external_level)

    def init_logger(self, quiet: bool = False) -> StdlibLikeLoguruAdapter:
        """Initialize logger with file and console handlers"""
        if MainLogger._configured:
            return self.logger

        self.ensure_log_path_exists()
        console_warning = _resolve_level(
            self.settings.log_level, fallback=logging.INFO
        )[1]
        file_level, file_warning = _resolve_level(
            self.settings.log_file_level, fallback=logging.INFO
        )

        stderr_level_name = "ERROR" if quiet else "WARNING"
        stdout_level_name = "SUCCESS" if quiet else "DEBUG"
        file_level_name = _level_no_to_name(file_level)

        LOGURU_LOGGER.remove()
        LOGURU_LOGGER.add(
            sys.stderr,
            level=stderr_level_name,
            format=LOGURU_FORMAT,
        )
        LOGURU_LOGGER.add(
            sys.stdout,
            level=stdout_level_name,
            format=LOGURU_FORMAT,
            filter=lambda record: record["level"].no < logging.WARNING,
        )
        LOGURU_LOGGER.add(
            str(self.log_file_path),
            level=file_level_name,
            format=LOGURU_FORMAT,
            colorize=False,
            rotation="2 weeks",
            retention=8,
            encoding="utf-8",
        )
        self.configure_stdlib_logging()

        if console_warning:
            self.logger.warning(console_warning)
        if file_warning:
            self.logger.warning(file_warning)

        self.logger.debug(
            f"Logging handlers configured. log_file_path={self.log_file_path}",
        )
        self.logger.info("Logger initialized successfully")
        MainLogger._configured = True
        return self.logger

    def format_exception_short(self, exc: Exception, limit: int = 1) -> str:
        """Return a short exception info showing last `limit` frames."""
        return format_exception_short(exc, limit=limit)

    def log_exception_short(
        self,
        exc: Exception,
        prefix: str = "",
        level: str = "error",
        limit: int = 1,
    ) -> None:
        """Log a short one-line/multi-line representation of an exception.

        - exc: exception instance
        - prefix: optional leading message shown before exception info (empty by default)
        - level: logger level to use ("error", "warning", "info", ...)
        - limit: how many traceback frames to include (default 1)
        """
        log_exception_short(
            log=self.log,
            exc=exc,
            prefix=prefix,
            level=level,
            limit=limit,
        )
