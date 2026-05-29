"""Diagram generation helpers for validated YAML files.

This module converts YAML files to PNG diagrams by piping `yml2dot` output
into Graphviz `dot`. It is intentionally small and focused: one public helper
processes a sequence of YAML files and reports generation status through logs.
"""

from typing import Sequence
from pathlib import Path
import subprocess
import tempfile
import re
import yaml
from loguru import logger

from src.logger import log_exception_short
from src.utils import count_timeout, _extract_job_view, _load_config_data


def _safe_job_filename(job_name: str) -> str:
    return re.sub(r"[^\w-]", "_", job_name)


def _build_selected_job_yaml(cfg_file: Path, job_name: str) -> Path | None:
    """Create temporary YAML containing only one selected job.

    Returns path to a temporary file. Caller is responsible for cleanup.
    """
    try:
        loaded = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
        payload = _extract_job_view(
            loaded, job_name=job_name, file_path=cfg_file)
    except (yaml.YAMLError, ValueError) as exc:
        logger.error(str(exc))
        return None
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", encoding="utf-8", delete=False
    )
    with tmp as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
    return Path(tmp.name)


def _build_yaml_from_supported_config(cfg_file: Path) -> Path | None:
    """Convert any supported config into temporary YAML for yml2dot."""
    try:
        loaded = _load_config_data(cfg_file)
    except Exception as exc:
        logger.error(f"Failed to parse {cfg_file}: {exc}")
        return None
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", encoding="utf-8", delete=False
    )
    with tmp as handle:
        yaml.safe_dump(loaded, handle, sort_keys=False, allow_unicode=True)
    return Path(tmp.name)


def build_dot_scheme(
    cfg_files: Sequence[Path],
    yml2dot_exec: Path,
    job_name: str | None = None,
    output_format: str = "svg",
) -> Path | None:
    """Build PNG diagrams for YAML files using `yml2dot` + `dot`.

    Note: timeout: is being counted automaticly

    Args:
        cfg_files: YAML files that already passed validation.
        yml2dot_exec: Path to the `yml2dot` executable.

    Returns:
        Path to the last generated PNG file on success.
        None if any file fails to convert.
    """
    last_output_file: Path | None = None

    for f in cfg_files:
        f = Path(f)
        output_file = (
            f.with_name(
                f"{f.stem}.{_safe_job_filename(job_name)}.{output_format}")
            if job_name
            else f.with_suffix(f".{output_format}")
        )
        timeout = count_timeout(fpath=f, tool="yml2dot")
        source_path = f
        temp_input: Path | None = None

        if f.suffix.lower() in (".json", ".toml"):
            temp_input = _build_yaml_from_supported_config(cfg_file=f)
            if temp_input is None:
                return None
            source_path = temp_input

        if job_name:
            source_for_job = source_path
            if source_for_job != f:
                # Use the already-converted temporary YAML as input for job extraction.
                source_for_job = source_path
            job_temp_input = _build_selected_job_yaml(
                cfg_file=source_for_job, job_name=job_name
            )
            if job_temp_input is None:
                if temp_input is not None:
                    temp_input.unlink(missing_ok=True)
                return None
            if temp_input is not None:
                temp_input.unlink(missing_ok=True)
            temp_input = job_temp_input
            source_path = job_temp_input

        try:
            # Run yml2dot first and fully collect stdout/stderr so we can
            # reliably validate its exit code and report errors.
            yml2dot_result = subprocess.run(
                [str(yml2dot_exec), str(source_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout,
            )

            if yml2dot_result.returncode != 0:
                stderr_text = yml2dot_result.stderr.decode(
                    errors="replace").strip()
                logger.error(
                    f"yml2dot failed for {f} with code {yml2dot_result.returncode}"
                )
                if stderr_text:
                    logger.error(f"yml2dot stderr: {stderr_text}")
                return None

            with open(output_file, "wb") as out:
                subprocess.run(
                    ["dot", f"-T{output_format}"],
                    input=yml2dot_result.stdout,
                    stdout=out,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=timeout,
                )

            logger.info(f"{f} -> {output_file} generated")
            last_output_file = output_file
        except subprocess.TimeoutExpired:
            logger.error(
                f"diagram generation timed out after {timeout}s on file: {f}")
            return None
        except subprocess.CalledProcessError as e:
            log_exception_short(
                logger,
                e,
                prefix=f"Failed to build diagram for {f}",
                level="error",
                limit=1,
            )
            if e.stderr:
                if isinstance(e.stderr, bytes):
                    stderr_text = e.stderr.decode(errors="replace").strip()
                else:
                    stderr_text = str(e.stderr).strip()
                logger.error(f"dot stderr: {stderr_text}")
            return None
        finally:
            if temp_input is not None:
                temp_input.unlink(missing_ok=True)

    return last_output_file
