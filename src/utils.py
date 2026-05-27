""""""


import sys
import logging
logger = logging.getLogger(__name__)

import sys
from pathlib import Path

from src.logger import log_exception_short


def _collect_yaml_files(yml_directory: Path) -> list[Path]:
    """Return all YAML files from a file path or recursively from a directory."""
    path = Path(yml_directory)

    if path.is_file():
        return [path] if path.suffix.lower() in (".yml", ".yaml") else []

    if not path.is_dir():
        logger.error("'%s' is neither a file nor directory", yml_directory)
        sys.exit(1)

    return sorted(list(path.rglob("*.yml")) + list(path.rglob("*.yaml")))


def check_for_empty_file(file_path: Path) -> int:
    """Return 1 if a file is empty or inaccessible, otherwise return 0."""
    try:
        if file_path.stat().st_size == 0:
            logger.error("%s is empty", file_path)
            return 1
        if not file_path.read_text(encoding="utf-8").strip():
            logger.error("%s contains only whitespace", file_path)
            return 1
    except OSError as e:
        log_exception_short(
            logger, e, prefix=f"Could not stat file {file_path}", level="error", limit=1
        )
        return 1
    return 0


def count_timeout(fpath: Path, tool: str) -> int | None:
    """
        Automaticly count timeout time for provided config files

        Args:
            fpath - config path
            exec - for what app is timeout being calculated

        Returns:
            timeount: int
    """
    if not fpath.exists():
        return None

    fsize_mb = fpath.stat().st_size / (1024 * 1024)

    if tool == "yml2dot":
        if fsize_mb <= 0.5:
            return 25
        elif fsize_mb <= 2.0:
            return 40
        else:
            return 80

    elif tool == "yq":
        if fsize_mb <= 2.0:
            return 20
        else:
            return 40
