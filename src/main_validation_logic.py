"""
YAML config validator — shell wrapper for yq via subprocess.
Runs basic + extensible checks and indentation validation.
Add this file to .gitignore if using locally.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re

from src.constants import (
    INDENT_SIZE,
    EXTENDED_CHECKS,
    DEPRECATED_ACTIONS,
    OPTIONAL_CHECKS,
)
from src.utils import _collect_yaml_files, check_for_empty_file, count_timeout
from src.dot_schemas import build_dot_scheme
from src.logger import log_exception_short
import subprocess
from pathlib import Path

from loguru import logger


def _normalize_action_ref(ref: str) -> tuple[str, str] | None:
    """Parse and normalize `action@version` references for exact matching."""
    if "@" not in ref:
        return None

    action, version = ref.split("@", 1)
    action = action.strip().strip("\"'").lower()
    version = version.strip().strip("\"'.,;:)").lower()

    if not action or not version:
        return None

    # Treat vX and X as equivalent labels, but keep full semantic parts.
    normalized_version = version[1:] if version.startswith("v") else version
    if not normalized_version:
        return None

    return action, normalized_version


def check_for_deprecated_keys(file_path: Path, content: str) -> int:
    """Return the number of deprecated GitHub Actions references in content."""
    issues = 0
    if not content:
        return 0

    found_refs = {
        parsed
        for raw_ref in re.findall(
            r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+){0,2}@[^\s\"']+", content
        )
        for parsed in [_normalize_action_ref(raw_ref)]
        if parsed is not None
    }

    for deprecated in DEPRECATED_ACTIONS:
        parsed_deprecated = _normalize_action_ref(deprecated)
        if parsed_deprecated is None:
            continue

        if parsed_deprecated in found_refs:
            logger.warning(f"{file_path} uses deprecated action '{deprecated}'")
            issues += 1

    return issues


def run_yq(
    fpath: Path,
    expression: str,
    description: str,
    yq_exec: Path,
    optional: bool = False,
) -> int:
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
                if optional:
                    logger.warning(f"{fpath}: {description} skipped (not present)")
                    return 0
                logger.error(f"{fpath}: {description} missing")
                return 1

        logger.info(f"{fpath}: {description} OK")
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
            logger.error(f"yq stderr: {stderr_text}")
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
                logger.error(f"{file_path}: line {i} mixed tabs/spaces")
                errors += 1
                continue

            if "\t" in indent:
                logger.warning(f"{file_path}: line {i} tab used (use spaces)")
                continue

            if indent and (len(indent) % INDENT_SIZE != 0):
                logger.warning(
                    f"{file_path}: line {i} indentation not a multiple of {INDENT_SIZE}"
                )

            if raw_line != raw_line.rstrip(" \t"):
                logger.warning(f"{file_path}: line {i} trailing spaces")

    return errors


def validate_config(
    yml_path: Path,
    yq_exec: Path,
    excluded_paths: list[Path],
    run_optional: bool = False,
) -> TypeError | int:
    """Validate YAML files and return validated files, or None on validation failure."""
    if not isinstance(yml_path, Path):
        raise TypeError("yml_directory is not proper Path object")
    total_errors = 0

    yaml_files = _collect_yaml_files(yml_path, excluded_paths)
    logger.info(f"Discovered YAML files: {yaml_files}\n\n")

    if not yaml_files:
        logger.warning(f"No YAML files found in '{yml_path}'")
        return 0

    for file_path in yaml_files:
        errors_before = total_errors
        logger.info(f"{'-' * 60}")
        logger.info(f"Checking: {file_path}")

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

        total_errors += run_yq_in_threadpool(
            fpath=file_path, yq_exec=yq_exec, run_optional=run_optional
        )

        total_errors += check_for_deprecated_keys(file_path, content)

        total_errors += check_indentation(file_path)
        cfg_error_qty = total_errors - errors_before
        logger.info(f"{'=' * 60}")
        if cfg_error_qty > 0:
            logger.warning(f"Errors found in {file_path} - {cfg_error_qty}\n\n")
        else:
            logger.success(f"Did not found errors in {file_path}\n\n")

    logger.info(f"{'=' * 60}")
    if total_errors > 0:
        logger.error(f"Total errors found: {total_errors}")
        return 1

    logger.info("YAML files are valid")
    return 0


def run_yq_in_threadpool(fpath: Path, yq_exec: Path, run_optional: bool = True) -> int:
    """Run a yq expression against a config file in ThreadPoolExecutor with automaticly counted threads.
    Return 0 on success, 1 on error."""
    total_errors = 0
    max_workers = max(1, (os.cpu_count() or 4) // 4)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                run_yq,
                fpath=fpath,
                expression=expr,
                description=f"check '{expr}'",
                yq_exec=yq_exec,
                optional=False,
            ): expr
            for expr in EXTENDED_CHECKS
        }
        if run_optional:
            futures |= {
                executor.submit(
                    run_yq,
                    fpath=fpath,
                    expression=expr,
                    description=f"check '{expr}'",
                    yq_exec=yq_exec,
                    optional=True,
                ): expr
                for expr in OPTIONAL_CHECKS
            }

        for future in as_completed(futures):
            total_errors += future.result()

    return total_errors


def regular_validation(
    cfg_files: Path,
    yq_exe: Path,
    excluded_paths: list[Path],
    yml2dot_exe: Path,
    run_optional: bool = False,
) -> int:
    """Run the non-schema validation pipeline and diagram generation.

    The pipeline validates YAML content with `yq`-based checks, then builds
    PNG diagrams for validated inputs.

    Args:
        cfg_files: Path to one YAML file or a directory with YAML files.
        yq_exe: Path to the `yq` executable.
        yml2dot_exe: Path to the `yml2dot` executable.

    Returns:
        0 when validation and diagram generation succeed.
        1 when validation fails or diagram generation fails.
    """
    logger.info(f"Running validate config task with optional checks: {run_optional}")
    res = validate_config(
        yml_path=cfg_files,
        yq_exec=yq_exe,
        run_optional=run_optional,
        excluded_paths=excluded_paths,
    )
    if res != 0:
        logger.error("Validation failed")
        return 1

    output_file = build_dot_scheme(
        cfg_files=_collect_yaml_files(cfg_files, excluded_paths),
        yml2dot_exec=yml2dot_exe,
    )
    if output_file is not None:
        logger.info(f"Successfully built dot schema, check results: {output_file}")
        logger.success("Pipeline finished successfully!")
        logger.info(f"{'-' * 60}")
        return 0

    logger.warning("Pipeline finished with fail")
    return 1
