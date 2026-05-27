"""Helpers for discovering external executables across operating systems."""

import shutil
from pathlib import Path
import sys
from typing import Sequence


def find_executable(
    filename: str, extra_paths: Sequence[Path | str] | None = None
) -> Path | None:
    """Find an executable in PATH first, then in known folders (non-recursive)."""
    path = shutil.which(filename)
    if path:
        return Path(path)

    default_dirs: list[Path] = []
    if sys.platform == "win32":
        default_dirs = [Path("C:/")]
    else:
        default_dirs = [
            Path("/usr/local/bin"),
            Path("/usr/bin"),
            Path("/opt/homebrew/bin"),
            Path("/usr/local/sbin"),
        ]

    if extra_paths:
        default_dirs += [Path(p) for p in extra_paths]

    for d in default_dirs:
        candidate = d / filename
        if candidate.exists():
            return candidate

    return None


def find_executable_recursive(fname: str, search_dir: Path | str) -> Path | None:
    """Recursively find an executable file inside the provided directory."""
    search_dir = Path(search_dir)
    if not search_dir.exists():
        return None
    for path in search_dir.rglob(fname):
        if path.exists():
            return path
    return None
