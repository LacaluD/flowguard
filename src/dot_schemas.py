"""Diagram generation helpers for validated YAML files.

This module converts YAML files to PNG diagrams by piping `yml2dot` output
into Graphviz `dot`. It is intentionally small and focused: one public helper
processes a sequence of YAML files and reports generation status through logs.
"""

from src.logger import log_exception_short
from src.utils import count_timeout
from typing import Sequence
from pathlib import Path
import subprocess
from loguru import logger


def build_dot_scheme(cfg_files: Sequence[Path], yml2dot_exec: Path) -> Path | None:
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
        output_file = f.with_suffix(".png")
        timeout = count_timeout(fpath=f, tool="yml2dot")
        try:
            # Run yml2dot first and fully collect stdout/stderr so we can
            # reliably validate its exit code and report errors.
            yml2dot_result = subprocess.run(
                [str(yml2dot_exec), str(f)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout,
            )

            if yml2dot_result.returncode != 0:
                stderr_text = yml2dot_result.stderr.decode(errors="replace").strip()
                logger.error(
                    f"yml2dot failed for {f} with code {yml2dot_result.returncode}"
                )
                if stderr_text:
                    logger.error(f"yml2dot stderr: {stderr_text}")
                return None

            with open(output_file, "wb") as out:
                subprocess.run(
                    ["dot", "-Tpng"],
                    input=yml2dot_result.stdout,
                    stdout=out,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=timeout,
                )

            logger.info(f"{f} -> {output_file} generated")
            last_output_file = output_file
        except subprocess.TimeoutExpired:
            logger.error(f"diagram generation timed out after {timeout}s on file: {f}")
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

    return last_output_file
