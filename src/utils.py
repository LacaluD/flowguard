""""""

import json
import tomllib

from src.logger import log_exception_short
from pathlib import Path
import sys
from loguru import logger
from typing import Any
from collections.abc import Mapping
import yaml


SUPPORTED_CONFIG_EXTENSIONS = (".yml", ".yaml", ".json", ".toml")


def _collect_yaml_files(
    yml_directory: Path, excluded_dirs: list[Path] | None = None
) -> list[Path]:
    """Return supported config files from a file path or recursively from a directory.

    Supported extensions: .yml, .yaml, .json, .toml.
    """
    path = Path(yml_directory)
    excluded_dirs = excluded_dirs or []

    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_CONFIG_EXTENSIONS else []

    if not path.exists():
        logger.error(f"'{yml_directory}' does not exist")
        sys.exit(1)

    if not path.is_dir() and not path.is_file():
        logger.error(f"'{yml_directory}' is neither a file nor directory")
        sys.exit(1)

    all_files = [
        file_path
        for ext in SUPPORTED_CONFIG_EXTENSIONS
        for file_path in path.rglob(f"*{ext}")
    ]

    return sorted(
        [
            f
            for f in all_files
            if not any(excluded in f.parents for excluded in excluded_dirs)
        ]
    )


def _load_config_data(cfg_file: Path) -> object:
    """Load config data from YAML, JSON, or TOML file."""
    suffix = cfg_file.suffix.lower()
    text = cfg_file.read_text(encoding="utf-8")
    if suffix in (".yml", ".yaml"):
        return yaml.safe_load(text)
    if suffix == ".json":
        return json.loads(text)
    if suffix == ".toml":
        return tomllib.loads(text)
    raise ValueError(f"Unsupported config format: {cfg_file.suffix}")


def check_for_empty_file(file_path: Path) -> int:
    """Return 1 if a file is empty or inaccessible, otherwise return 0."""
    try:
        if file_path.stat().st_size == 0:
            logger.error(f"{file_path} is empty")
            return 1
        if not file_path.read_text(encoding="utf-8").strip():
            logger.error(f"{file_path} contains only whitespace")
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

    return None


def _extract_job_view(data: Any, job_name: str, file_path: Path) -> dict[str, Any]:
    """Return a minimal config that contains only one selected job.

    Args:
        data: Parsed config object.
        job_name: Job key to extract from top-level ``jobs`` mapping.
        file_path: Source file path, used in error messages.

    Returns:
        A mapping with only the selected job.

    Raises:
        ValueError: If config structure is invalid or job was not found.
    """
    if not isinstance(data, Mapping):
        raise ValueError(f"{file_path}: expected mapping root to select --job")

    jobs = data.get("jobs")
    if not isinstance(jobs, Mapping):
        raise ValueError(f"{file_path}: top-level 'jobs' mapping is missing")

    if job_name not in jobs:
        raise ValueError(
            f"{file_path}: job '{job_name}' not found under 'jobs'")

    selected: dict[str, Any] = {"jobs": {job_name: jobs[job_name]}}
    if "name" in data:
        selected["name"] = data["name"]
    return selected
