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
import logging
logger = logging.getLogger(__name__)


def build_dot_scheme(yml_files: Sequence[Path], yml2dot_exec: Path) -> Path | None:
    """Build PNG diagrams for YAML files using `yml2dot` + `dot`.

    Note: timeout: is being counted automaticly

    Args:
        yml_files: YAML files that already passed validation.
        yml2dot_exec: Path to the `yml2dot` executable.

    Returns:
        Path to the last generated PNG file on success.
        None if any file fails to convert.
    """
    last_output_file: Path | None = None


    for f in yml_files:
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
                stderr_text = yml2dot_result.stderr.decode(
                    errors="replace").strip()
                logger.error("yml2dot failed for %s with code %d",
                             f, yml2dot_result.returncode)
                if stderr_text:
                    logger.error("yml2dot stderr: %s", stderr_text)
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

            logger.info("%s -> %s generated", f, output_file)
            last_output_file = output_file
        except subprocess.TimeoutExpired:
            logger.error(
                "diagram generation timed out after %ss on file: %s", timeout, f)
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
                logger.error("dot stderr: %s", stderr_text)
            return None

    return last_output_file
