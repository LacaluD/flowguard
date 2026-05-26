import io
import logging
import sys
from pathlib import Path
from unittest.mock import patch

import yaml
import pytest

from main import main


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


def _fake_validation_main(*, yml_path: Path, yq_exec: Path) -> list[Path] | None:
    try:
        yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        return [yml_path]
    except yaml.YAMLError:
        logging.getLogger(__name__).error("Validation failed for %s", yml_path)
        return None


def run_and_capture(yml_file: Path) -> str:
    """Run CLI validation and capture stdout for golden comparison."""
    captured = io.StringIO()

    with patch("sys.stdout", captured):
        with patch("src.logger.MainLogger.init_logger", side_effect=lambda quiet=False: _configure_test_logging(quiet=quiet)):
            with patch("main.find_executable", side_effect=lambda _: Path("/bin/tool")):
                with patch("main.find_executable_recursive", side_effect=lambda **_: Path("/bin/tool")):
                    with patch("main.validation_main", side_effect=_fake_validation_main):
                        with patch("main.build_dot_scheme", side_effect=lambda **_: Path("result.png")):
                            with patch("sys.argv", ["main.py", "--yml-files", str(yml_file)]):
                                main()

    return captured.getvalue().strip()


@pytest.mark.parametrize("case_dir", _iter_case_dirs())
def test_golden(case_dir: Path, request: pytest.FixtureRequest) -> None:
    yml_file = next(case_dir.glob("*.yml"), None)
    if yml_file is None:
        yml_file = next(case_dir.glob("*.yaml"))

    expected_file = next(case_dir.glob("*.expected.txt"))
    actual = run_and_capture(yml_file)

    if request.config.getoption("--update-golden", default=False):
        expected_file.write_text(actual, encoding="utf-8")
        return

    expected = expected_file.read_text(encoding="utf-8").strip()
    assert actual == expected, (
        f"\nGolden file mismatch for {case_dir.name}\n"
        f"Expected:\n{expected}\n"
        f"Actual:\n{actual}"
    )
