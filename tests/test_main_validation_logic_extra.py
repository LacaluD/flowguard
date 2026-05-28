import subprocess
from pathlib import Path

import pytest

from src import main_validation_logic


def test_run_yq_timeout_returns_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=5)

    monkeypatch.setattr(main_validation_logic.subprocess, "run", raise_timeout)
    monkeypatch.setattr(main_validation_logic, "count_timeout", lambda **_: 5)

    assert main_validation_logic.run_yq(yml_file, ".", "base", Path("yq")) == 1


def test_check_indentation_warn_paths_do_not_return_errors(tmp_path: Path) -> None:
    yml_file = tmp_path / "indent.yml"
    # Non-multiple indent and trailing spaces should be warnings only.
    yml_file.write_text("a:\n   b: 1  \n", encoding="utf-8")

    assert main_validation_logic.check_indentation(yml_file) == 0


def test_validate_config_read_text_error_returns_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda _: [yml_file]
    )
    monkeypatch.setattr(main_validation_logic, "check_for_empty_file", lambda _: 0)

    def raise_read_error(*args, **kwargs):
        raise OSError("cannot read")

    monkeypatch.setattr(Path, "read_text", raise_read_error, raising=False)

    assert main_validation_logic.validate_config(tmp_path, Path("yq")) == 1


def test_regular_validation_returns_one_when_build_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(main_validation_logic, "validate_config", lambda **_: 0)
    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda _: [yml_file]
    )
    monkeypatch.setattr(main_validation_logic, "build_dot_scheme", lambda **_: None)

    assert (
        main_validation_logic.regular_validation(
            cfg_files=yml_file,
            yq_exe=Path("yq"),
            yml2dot_exe=Path("yml2dot"),
        )
        == 1
    )


def test_regular_validation_returns_zero_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(main_validation_logic, "validate_config", lambda **_: 0)
    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda _: [yml_file]
    )
    monkeypatch.setattr(
        main_validation_logic,
        "build_dot_scheme",
        lambda **_: yml_file.with_suffix(".png"),
    )

    assert (
        main_validation_logic.regular_validation(
            cfg_files=yml_file,
            yq_exe=Path("yq"),
            yml2dot_exe=Path("yml2dot"),
        )
        == 0
    )
