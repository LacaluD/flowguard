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
    YAML_ONLY_CHECKS,
)
from src.utils import (
    _collect_yaml_files,
    check_for_empty_file,
    count_timeout,
    _load_config_data,
    finalize_dot_pipeline,
    ensure_single_cfg_file,
)
from src.dot_schemas import build_dot_scheme
from src.logger import log_exception_short
import subprocess
from pathlib import Path
import yaml

from loguru import logger


class ValidationPipeline:
    def __init__(self, yq_exe: Path, excluded_paths: list[Path], run_optional: bool = False):
        self.yq_exe = yq_exe
        self.excluded_paths = excluded_paths
        self.run_optional = run_optional

    def _materialize_yaml_for_validation(self, cfg_file: Path) -> Path:
        """Create temporary YAML equivalent for non-YAML config files."""
        loaded = _load_config_data(cfg_file)
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", encoding="utf-8", delete=False
        )
        with temp_file as handle:
            yaml.safe_dump(loaded, handle, sort_keys=False, allow_unicode=True)
        return Path(temp_file.name)

    def _normalize_action_ref(self, ref: str) -> tuple[str, str] | None:
        """Parse and normalize `action@version` references for exact matching."""
        if "@" not in ref:
            return None

        action, version = ref.split("@", 1)
        action = action.strip().strip("\"'").lower()
        version = version.strip().strip("\"'.,;:)").lower()

        if not action or not version:
            return None

        # Treat vX and X as equivalent labels, but keep full semantic parts.
        normalized_version = version[1:] if version.startswith(
            "v") else version
        if not normalized_version:
            return None

        return action, normalized_version

    def check_for_deprecated_keys(self, file_path: Path, content: str) -> int:
        """Return the number of deprecated GitHub Actions references in content."""
        issues = 0
        if not content:
            return 0

        found_refs = {
            parsed
            for raw_ref in re.findall(
                r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+){0,2}@[^\s\"']+", content
            )
            for parsed in [self._normalize_action_ref(raw_ref)]
            if parsed is not None
        }

        for deprecated in DEPRECATED_ACTIONS:
            parsed_deprecated = self._normalize_action_ref(deprecated)
            if parsed_deprecated is None:
                continue

            if parsed_deprecated in found_refs:
                logger.warning(
                    f"{file_path} uses deprecated action '{deprecated}'")
                issues += 1

        return issues

    def run_yq(self,
               fpath: Path,
               expression: str,
               description: str,
               ) -> int:
        """Run a yq expression against a YAML file and return 0 on success, 1 on error."""
        try:
            timeout = count_timeout(fpath=fpath, tool="yml2dot")

            result = subprocess.run(
                [self.yq_exe, "eval", expression, str(fpath)],
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
                    if self.run_optional:
                        logger.warning(
                            f"{fpath}: {description} skipped (not present)")
                        return 0
                    logger.error(f"{fpath}: {description} missing")
                    return 1

            logger.info(f"{fpath}: {description} OK")
            return 0
        except subprocess.TimeoutExpired as exc:
            log_exception_short(
                logger,
                exc,
                prefix=f"yq timed out after {timeout}s on file: {fpath}",
                level="error",
            )

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

    def check_indentation(self, file_path: Path) -> int:
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
                    logger.warning(
                        f"{file_path}: line {i} tab used (use spaces)")
                    continue

                if indent and (len(indent) % INDENT_SIZE != 0):
                    logger.warning(
                        f"{file_path}: line {i} indentation not a multiple of {INDENT_SIZE}"
                    )

                if raw_line != raw_line.rstrip(" \t"):
                    logger.warning(f"{file_path}: line {i} trailing spaces")

        return errors

    def validate_config(self,
                        yml_path: Path,
                        ) -> TypeError | int:
        """Validate config files and return 0 on success, 1 on any failure."""
        if not isinstance(yml_path, Path):
            raise TypeError("yml_directory is not proper Path object")
        total_errors = 0

        config_files = _collect_yaml_files(yml_path, self.excluded_paths)
        logger.info(f"Discovered config files: {config_files}\n\n")

        if not config_files:
            logger.warning(f"No config files found in '{yml_path}'")
            return 0

        for file_path in config_files:
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

            temp_yaml_for_validation: Path | None = None
            validation_target = file_path

            try:
                if file_path.suffix.lower() in (".json", ".toml"):
                    temp_yaml_for_validation = self._materialize_yaml_for_validation(
                        file_path)
                    validation_target = temp_yaml_for_validation

                total_errors += self.run_yq(
                    fpath=validation_target,
                    expression=".",
                    description="base syntax check",
                )

                total_errors += self.run_yq_in_threadpool(
                    fpath=validation_target,
                    fending=yml_path.suffix,
                )
            except Exception as e:
                log_exception_short(
                    logger,
                    e,
                    prefix=f"Cannot prepare config {file_path} for validation",
                    level="error",
                    limit=1,
                )
                total_errors += 1
            finally:
                if temp_yaml_for_validation is not None:
                    temp_yaml_for_validation.unlink(missing_ok=True)

            total_errors += self.check_for_deprecated_keys(file_path, content)

            if file_path.suffix.lower() in (".yml", ".yaml"):
                total_errors += self.check_indentation(file_path)
            cfg_error_qty = total_errors - errors_before
            logger.info(f"{'=' * 60}")
            if cfg_error_qty > 0:
                logger.warning(
                    f"Errors found in {file_path} - {cfg_error_qty}\n\n")
            else:
                logger.success(
                    f"Errors found in {file_path} - {cfg_error_qty}\n\n")

        logger.info(f"{'=' * 60}")
        if total_errors > 0:
            logger.error(f"Total errors found: {total_errors}")
            return 1

        logger.info("Config files are valid")
        return 0

    def run_yq_in_threadpool(self, fpath: Path, fending: str
                             ) -> int:
        """
            Run a yq expression against a config file in ThreadPoolExecutor with automaticly counted threads.
            Return 0 on success, 1 on error.
        """
        total_errors = 0
        max_workers = max(1, (os.cpu_count() or 4) // 4)

        checks = EXTENDED_CHECKS.copy()
        if fending in (".yml", ".yaml"):
            checks = EXTENDED_CHECKS.copy() + YAML_ONLY_CHECKS

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.run_yq,
                    fpath=fpath,
                    expression=expr,
                    description=f"check '{expr}'",
                ): expr
                for expr in checks
            }
            if self.run_optional:
                futures |= {
                    executor.submit(
                        self.run_yq,
                        fpath=fpath,
                        expression=expr,
                        description=f"check '{expr}'",
                    ): expr
                    for expr in OPTIONAL_CHECKS
                }

            for future in as_completed(futures):
                total_errors += future.result()

        return total_errors

    def _build_job_scoped_validation_yaml(self, cfg_file: Path, job_name: str) -> Path | None:
        """Create temporary YAML used to validate only one selected job.

        The scoped payload keeps top-level keys that are covered by required checks
        (``name`` and ``on``), and narrows ``jobs`` to a single entry.
        """
        try:
            loaded = _load_config_data(cfg_file)
        except Exception as exc:
            log_exception_short(
                logger,
                exc,
                prefix=f"Failed to parse {cfg_file} for --job validation: {exc}",
                level="error",
            )
            return None

        if not isinstance(loaded, dict):
            logger.error(f"{cfg_file}: root must be mapping to use --job")
            return None

        jobs = loaded.get("jobs")
        if not isinstance(jobs, dict):
            logger.error(f"{cfg_file}: top-level 'jobs' mapping is missing")
            return None

        if job_name not in jobs:
            logger.error(
                f"{cfg_file}: job '{job_name}' not found under 'jobs'")
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
            yaml.safe_dump(payload, handle, sort_keys=False,
                           allow_unicode=True)

        return Path(temp_file.name)

    def regular_validation(self,
                           cfg_files: Sequence[Path],
                           yml2dot_exe: Path,
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
        cfg_file = ensure_single_cfg_file(cfg_files=cfg_files, mode_name="Regular validation")
        if cfg_file is None:
            return 1

        logger.info(
            f"Running validate config task with optional checks: {self.run_optional}")
        yaml_files = _collect_yaml_files(cfg_file, self.excluded_paths)
        temp_job_files: list[Path] = []

        try:
            if job_name:
                logger.info(
                    f"Job-scoped validation enabled for job: {job_name}")
                for source_file in yaml_files:
                    temp_job_file = self._build_job_scoped_validation_yaml(
                        cfg_file=source_file, job_name=job_name
                    )
                    if temp_job_file is None:
                        logger.error("Validation failed")
                        return 1
                    temp_job_files.append(temp_job_file)

                for temp_job_file in temp_job_files:
                    res = self.validate_config(
                        yml_path=temp_job_file,
                    )
                    if res != 0:
                        return 1
            else:
                res = self.validate_config(
                    yml_path=cfg_file,
                )
                if res != 0:
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

        return finalize_dot_pipeline(output_file)
