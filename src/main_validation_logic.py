"""
YAML config validator — shell wrapper for yq via subprocess.
Runs basic + extensible checks and indentation validation.
Add this file to .gitignore if using locally.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
import tempfile
from collections.abc import Sequence

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
import yaml

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


def _build_job_scoped_validation_yaml(cfg_file: Path, job_name: str) -> Path | None:
    """Create temporary YAML used to validate only one selected job.

    The scoped payload keeps top-level keys that are covered by required checks
    (``name`` and ``on``), and narrows ``jobs`` to a single entry.
    """
    try:
        loaded = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error(f"Failed to parse {cfg_file} for --job validation: {exc}")
        return None

    if not isinstance(loaded, dict):
        logger.error(f"{cfg_file}: root must be mapping to use --job")
        return None

    jobs = loaded.get("jobs")
    if not isinstance(jobs, dict):
        logger.error(f"{cfg_file}: top-level 'jobs' mapping is missing")
        return None

    if job_name not in jobs:
        logger.error(f"{cfg_file}: job '{job_name}' not found under 'jobs'")
        return None

    payload: dict[str, object] = {"jobs": {job_name: jobs[job_name]}}
    if "name" in loaded:
        payload["name"] = loaded["name"]

    # PyYAML may coerce unquoted `on:` key to boolean True.
    if "on" in loaded:
        payload["on"] = loaded["on"]
    elif True in loaded:
        payload["on"] = loaded[True]

    temp_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", encoding="utf-8", delete=False
    )
    with temp_file as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)

    return Path(temp_file.name)


def regular_validation(
    cfg_files: Sequence[Path],
    yq_exe: Path,
    excluded_paths: list[Path],
    yml2dot_exe: Path,
    run_optional: bool = False,
    job_name: str | None = None,
    output_format: str = "svg",
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
    if len(cfg_files) > 1:
        logger.error(
            f"regular validation requires exactly one config file, got {len(cfg_files)}"
        )
        return 1

    if not cfg_files:
        logger.error("regular validation requires at least one config file")
        return 1

    cfg_file = cfg_files[0]

    logger.info(f"Running validate config task with optional checks: {run_optional}")
    yaml_files = _collect_yaml_files(cfg_file, excluded_paths)
    temp_job_files: list[Path] = []

    try:
        if job_name:
            logger.info(f"Job-scoped validation enabled for job: {job_name}")
            for source_file in yaml_files:
                temp_job_file = _build_job_scoped_validation_yaml(
                    cfg_file=source_file, job_name=job_name
                )
                if temp_job_file is None:
                    logger.error("Validation failed")
                    return 1
                temp_job_files.append(temp_job_file)

            for temp_job_file in temp_job_files:
                res = validate_config(
                    yml_path=temp_job_file,
                    yq_exec=yq_exe,
                    run_optional=run_optional,
                    excluded_paths=[],
                )
                if res != 0:
                    logger.error("Validation failed")
                    return 1
        else:
            res = validate_config(
                yml_path=cfg_file,
                yq_exec=yq_exe,
                run_optional=run_optional,
                excluded_paths=excluded_paths,
            )
            if res != 0:
                logger.error("Validation failed")
                return 1

        output_file = build_dot_scheme(
            cfg_files=yaml_files,
            yml2dot_exec=yml2dot_exe,
            job_name=job_name,
            output_format=output_format,
        )
    finally:
        for temp_job_file in temp_job_files:
            temp_job_file.unlink(missing_ok=True)

    if output_file is not None:
        logger.info(f"Successfully built dot schema, check results: {output_file}")
        logger.success("Pipeline finished successfully!")
        logger.info(f"{'-' * 60}")
        return 0

    logger.warning("Pipeline finished with fail")
    return 1
