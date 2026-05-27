"""
YAML config validator — shell wrapper for yq via subprocess.
Runs basic + extensible checks and indentation validation.
Add this file to .gitignore if using locally.
"""

from src.constants import INDENT_SIZE, EXTENDED_CHECKS, DEPRECATED_ACTIONS
from src.utils import _collect_yaml_files, check_for_empty_file, count_timeout
from src.dot_schemas import build_dot_scheme
from src.logger import log_exception_short
import subprocess
from pathlib import Path

import logging

logger = logging.getLogger(__name__)


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
        timeout = count_timeout(fpath=fpath, tool="yml2dot")

        result = subprocess.run(
            [yq_exec, "eval", expression, str(fpath)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )

        output = result.stdout.strip()
        # For extended checks, treat empty/null as a missing field.
        if expression != ".":
            if output in ("", "null", "false"):
                logger.error("%s: %s missing", fpath, description)
                return 1

        logger.info("%s: %s OK", fpath, description)
        return 0
    except subprocess.TimeoutExpired:
        logger.error(f"yq timed out after {timeout}s on file: {fpath}")
        return 1
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


def validate_config(yml_path: Path, yq_exec: Path) -> TypeError | int:
    """Validate YAML files and return validated files, or None on validation failure."""
    if not isinstance(yml_path, Path):
        raise TypeError("yml_directory is not proper Path object")
    total_errors = 0

    yaml_files = _collect_yaml_files(yml_path)
    logger.debug("Discovered YAML files: %s", yaml_files)

    if not yaml_files:
        logger.warning("No YAML files found in '%s'", yml_path)
        return 0

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
        return 1

    logger.info("YAML files are valid")
    return 0


def regular_validation(yml_files: Path, yq_exe: Path, yml2dot_exe: Path) -> int:
    """Run the non-schema validation pipeline and diagram generation.

    The pipeline validates YAML content with `yq`-based checks, then builds
    PNG diagrams for validated inputs.

    Args:
        yml_files: Path to one YAML file or a directory with YAML files.
        yq_exe: Path to the `yq` executable.
        yml2dot_exe: Path to the `yml2dot` executable.

    Returns:
        0 when validation and diagram generation succeed.
        1 when validation fails or diagram generation fails.
    """
    res = validate_config(yml_path=yml_files, yq_exec=yq_exe)
    if res != 0:
        logger.error("Validation failed")
        return 1

    output_file = build_dot_scheme(
        yml_files=_collect_yaml_files(yml_files),
        yml2dot_exec=yml2dot_exe,
    )
    if output_file is not None:
        logger.info(f"Successfully built dot schema, check results: {output_file}")
        logger.info("Pipeline finished successfully!")
        return 0

    return 1
