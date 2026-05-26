"""Main logger module"""

import logging
import os
import sys
import traceback
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Final


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
    log: logging.Logger,
    exc: Exception,
    prefix: str = "",
    level: str = "error",
    limit: int = 1,
) -> None:
    """Log a compact exception message with optional traceback tail.

    Args:
        log: Standard library logger instance.
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


LOG_FORMAT: Final[str] = (
    "[%(asctime)s] [%(levelname)-8s] %(name)s:%(funcName)s:%(lineno)d - %(message)s"
)
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def _resolve_level(level_name: str, fallback: int = logging.INFO) -> tuple[int, str | None]:
    """Resolve a string log level to stdlib int level with optional warning."""
    normalized = (level_name or "").strip().upper()
    if hasattr(logging, normalized):
        maybe_level = getattr(logging, normalized)
        if isinstance(maybe_level, int):
            return maybe_level, None

    warning_message = f"Invalid log level '{level_name}'. Fallback to {logging.getLevelName(fallback)} was applied."
    return fallback, warning_message


class MainLogger:
    """Main project logger"""

    _configured: bool = False

    def __init__(self, logger_name: str = "ymlvalidator"):
        self.logger_name = logger_name
        self.logger = logging.getLogger(logger_name)
        self.log = self.logger
        self.settings = get_settings()
        self.log_dir_path, self.log_file_path = _resolve_log_paths()

    def ensure_log_path_exists(self) -> None:
        """Get root path for logs dir and check if they are exists"""
        self.log_dir_path.mkdir(parents=True, exist_ok=True)
        self.log_file_path.touch(exist_ok=True)

    def configure_stdlib_logging(self) -> None:
        """Configure external stdlib loggers to respect project settings."""
        external_level, _ = _resolve_level(self.settings.external_log_level)

        for logger_name in ("aiohttp", "asyncio"):
            external_logger = logging.getLogger(logger_name)
            external_logger.setLevel(external_level)
            external_logger.propagate = True

        for logger_name in ("telethon", "telethon.network", "telethon.client"):
            external_logger = logging.getLogger(logger_name)
            external_logger.setLevel(external_level)
            external_logger.propagate = True

    def resolve_file_log_level(self) -> tuple[str, str | None]:
        """Validate LOG_FILE_LEVEL and return safe value with optional warning text."""
        _, warning = _resolve_level(
            self.settings.log_file_level, fallback=logging.INFO)
        return self.settings.log_file_level, warning

    def init_logger(self, quiet: bool = False) -> logging.Logger:
        """Initialize logger with file and console handlers"""
        if MainLogger._configured:
            return self.logger

        self.ensure_log_path_exists()
        console_level, console_warning = _resolve_level(
            self.settings.log_level, fallback=logging.INFO)
        file_level, file_warning = _resolve_level(
            self.settings.log_file_level, fallback=logging.INFO)

        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.ERROR if quiet else logging.WARNING)
        stderr_handler.setFormatter(formatter)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(
            logging.CRITICAL + 1 if quiet else logging.DEBUG)
        stdout_handler.addFilter(
            lambda record: record.levelno < logging.WARNING)
        stdout_handler.setFormatter(formatter)

        file_handler = TimedRotatingFileHandler(
            filename=str(self.log_file_path),
            when="W0",
            interval=2,
            backupCount=8,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.handlers = []
        root_logger.addHandler(stderr_handler)
        root_logger.addHandler(stdout_handler)
        root_logger.addHandler(file_handler)

        self.configure_stdlib_logging()

        if console_warning:
            self.logger.warning(console_warning)
        if file_warning:
            self.logger.warning(file_warning)

        self.logger.debug(
            "Logging handlers configured. log_file_path=%s", self.log_file_path)
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
