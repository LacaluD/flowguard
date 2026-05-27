import io
import logging
import re
import sys
from pathlib import Path
from unittest.mock import patch

import yaml
import pytest

from main import main
from version import __version__, __build__, __commit__

GOLDEN_DIR = Path(__file__).parent / "golden"


def _iter_case_dirs() -> list[Path]:
    return sorted([path for path in GOLDEN_DIR.iterdir() if path.is_dir()])


def _configure_test_logging(quiet: bool = False) -> logging.Logger:
    root = logging.getLogger()
    root.handlers = []
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.ERROR if quiet else logging.INFO)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(handler)

    return logging.getLogger("golden")


def _fake_regular_validation(*, yml_files: Path, yq_exe: Path, yml2dot_exe: Path) -> int:
    try:
        yaml.safe_load(yml_files.read_text(encoding="utf-8"))
        logging.getLogger(__name__).info(
            "Successfully built dot schema, check results: result.png"
        )
        logging.getLogger(__name__).info("Pipeline finished successfully!")
        return 0
    except yaml.YAMLError:
        logging.getLogger(__name__).error(
            "Validation failed for %s", yml_files)
        return 1


def run_and_capture(yml_file: Path) -> str:
    """Run CLI validation and capture stdout for golden comparison."""
    captured = io.StringIO()

    with patch("sys.stdout", captured):
        with patch(
            "src.logger.MainLogger.init_logger",
            side_effect=lambda quiet=False: _configure_test_logging(
                quiet=quiet),
        ):
            with patch("main.find_executable", side_effect=lambda _: Path("/bin/tool")):
                with patch(
                    "main.find_executable_recursive",
                    side_effect=lambda **_: Path("/bin/tool"),
                ):
                    with patch(
                        "main.regular_validation", side_effect=_fake_regular_validation
                    ):
                        with patch(
                            "sys.argv", ["main.py",
                                         "--yml-files", str(yml_file)]
                        ):
                            main()

    return captured.getvalue().strip()


def _normalize_dynamic_startup_line(text: str) -> str:
    """Normalize dynamic build/commit values to keep golden output stable."""
    return re.sub(
        r"\(build [^,]+, commit [^)]+\)",
        "(build __dev__, commit __dev__)",
        text,
    )


def _assert_startup_line_matches_version(actual_output: str) -> None:
    """Ensure startup log line uses version/build/commit from version.py."""
    lines = actual_output.splitlines()
    assert lines, "CLI output is empty"

    expected_startup = (
        f"INFO: Starting YMLValidator {__version__} "
        f"(build {__build__}, commit {__commit__})"
    )
    assert lines[0] == expected_startup


@pytest.mark.parametrize("case_dir", _iter_case_dirs())
def test_golden(case_dir: Path, request: pytest.FixtureRequest) -> None:
    yml_file = next(case_dir.glob("*.yml"), None)
    if yml_file is None:
        yml_file = next(case_dir.glob("*.yaml"))

    expected_file = next(case_dir.glob("*.expected.txt"))
    actual_raw = run_and_capture(yml_file)
    _assert_startup_line_matches_version(actual_raw)
    actual = _normalize_dynamic_startup_line(actual_raw)

    if request.config.getoption("--update-golden", default=False):
        expected_file.write_text(actual, encoding="utf-8")
        return

    expected = _normalize_dynamic_startup_line(
        expected_file.read_text(encoding="utf-8").strip()
    )
    assert actual == expected, (
        f"\nGolden file mismatch for {case_dir.name}\n"
        f"Expected:\n{expected}\n"
        f"Actual:\n{actual}"
    )
