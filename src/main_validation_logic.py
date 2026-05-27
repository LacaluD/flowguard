"""
YAML config validator — shell wrapper for yq via subprocess.
Runs basic + extensible checks and indentation validation.
Add this file to .gitignore if using locally.
"""

import sys
import subprocess
from pathlib import Path
from typing import Sequence

import logging

logger = logging.getLogger(__name__)

from src.utils import _collect_yaml_files, check_for_empty_file
from src.logger import log_exception_short
from src.constants import INDENT_SIZE, EXTENDED_CHECKS, DEPRECATED_ACTIONS


def check_for_deprecated_keys(file_path: Path, content: str) -> int:
    """Return the number of deprecated GitHub Actions references in content."""
    issues = 0
    if not content:
        return 0

    for deprecated in DEPRECATED_ACTIONS:
        if deprecated in content:
            logger.warning("%s uses deprecated action '%s'", file_path, deprecated)
            issues += 1

    return issues


def run_yq(fpath: Path, expression: str, description: str, yq_exec: Path) -> int:
    """Run a yq expression against a YAML file and return 0 on success, 1 on error."""
    try:
        result = subprocess.run(
            [yq_exec, "eval", expression, str(fpath)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        output = result.stdout.strip()
        # For extended checks, treat empty/null as a missing field.
        if expression != ".":
            if output in ("", "null"):
                logger.error("%s: %s missing", fpath, description)
                return 1

        logger.info("%s: %s OK", fpath, description)
        return 0

    except subprocess.CalledProcessError as e:
        log_exception_short(
            logger,
            e,
            prefix=f"{fpath}: {description} failed",
            level="error",
            limit=1,
        )
        stderr_text = (e.stderr or "").strip()
        if stderr_text:
            logger.error("yq stderr: %s", stderr_text)
        return 1


def check_indentation(file_path: Path) -> int:
    """Check indentation/whitespace issues and return the number of hard errors."""
    errors = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            raw_line = line.rstrip("\r\n")

            if not raw_line.strip():
                continue

            stripped = raw_line.lstrip("\t ")
            indent = raw_line[: len(raw_line) - len(stripped)]

            # Mixed tabs/spaces are treated as a hard formatting error.
            if "\t" in indent and " " in indent:
                logger.error("%s: line %d mixed tabs/spaces", file_path, i)
                errors += 1
                continue

            if "\t" in indent:
                logger.warning("%s: line %d tab used (use spaces)", file_path, i)
                continue

            if indent and (len(indent) % INDENT_SIZE != 0):
                logger.warning(
                    "%s: line %d indentation not a multiple of %d",
                    file_path,
                    i,
                    INDENT_SIZE,
                )

            if raw_line != raw_line.rstrip(" \t"):
                logger.warning("%s: line %d trailing spaces", file_path, i)

    return errors


def validation_main(yml_path: Path, yq_exec: Path) -> list[Path] | None:
    """Validate YAML files and return validated files, or None on validation failure."""
    if not isinstance(yml_path, Path):
        raise TypeError("yml_directory is not proper Path object")
    total_errors = 0

    yaml_files = _collect_yaml_files(yml_path)
    logger.debug("Discovered YAML files: %s", yaml_files)

    if not yaml_files:
        logger.warning("No YAML files found in '%s'", yml_path)
        return None

    for file_path in yaml_files:
        logger.info("%s", "-" * 60)
        logger.info("Checking: %s", file_path)

        total_errors += check_for_empty_file(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            log_exception_short(
                logger, e, prefix=f"Cannot read {file_path}", level="error", limit=1
            )
            total_errors += 1
            continue

        total_errors += run_yq(
            fpath=file_path,
            expression=".",
            description="base syntax check",
            yq_exec=yq_exec,
        )

        for expr in EXTENDED_CHECKS:
            total_errors += run_yq(
                fpath=file_path,
                expression=expr,
                description=f"check '{expr}'",
                yq_exec=yq_exec,
            )

        total_errors += check_for_deprecated_keys(file_path, content)

        total_errors += check_indentation(file_path)

    logger.info("%s", "=" * 60)
    if total_errors > 0:
        logger.error("Total errors found: %d", total_errors)
        return None

    logger.info("YAML files are valid")
    return yaml_files


def build_dot_scheme(yml_files: Sequence[Path], yml2dot_exec: Path) -> Path | None:
    """Generate PNG diagrams from validated YAML files and return the last output path."""
    last_output_file: Path | None = None

    for f in yml_files:
        f = Path(f)
        output_file = f.with_suffix(".png")
        try:
            yml2dot_proc = subprocess.Popen(
                [str(yml2dot_exec), str(f)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            with open(output_file, "wb") as out:
                subprocess.run(
                    ["dot", "-Tpng"],
                    stdin=yml2dot_proc.stdout,
                    stdout=out,
                    stderr=subprocess.PIPE,
                    check=True,
                )
            yml2dot_proc.wait()
            logger.info("%s -> %s generated", f, output_file)
            last_output_file = output_file
        except subprocess.CalledProcessError as e:
            log_exception_short(
                logger,
                e,
                prefix=f"Failed to build diagram for {f}",
                level="error",
                limit=1,
            )
            if e.stderr:
                logger.error(
                    "dot stderr: %s", e.stderr.decode(errors="replace").strip()
                )
            return None

    return last_output_file
