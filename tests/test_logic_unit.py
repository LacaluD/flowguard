import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import main_validation_logic


def test_find_yaml_files_with_yaml_file_returns_single_path(tmp_path: Path) -> None:
    yml_file = tmp_path / "ci.yml"
    yml_file.write_text("name: test\n", encoding="utf-8")

    result = main_validation_logic._collect_yaml_files(yml_file)

    assert result == [yml_file]


def test_find_yaml_files_with_non_yaml_file_returns_empty_list(tmp_path: Path) -> None:
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("hello\n", encoding="utf-8")

    result = main_validation_logic._collect_yaml_files(txt_file)

    assert result == []


def test_find_yaml_files_with_directory_collects_yml_and_yaml(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    yml_file = tmp_path / "root.yml"
    yaml_file = tmp_path / "a" / "nested.yaml"
    yml_file.write_text("name: root\n", encoding="utf-8")
    yaml_file.write_text("name: nested\n", encoding="utf-8")

    result = main_validation_logic._collect_yaml_files(tmp_path)

    assert sorted(result) == sorted([yml_file, yaml_file])


def test_find_yaml_files_raises_system_exit_for_invalid_path(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main_validation_logic._collect_yaml_files(tmp_path / "missing")


def test_check_for_empty_file_returns_one_for_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.yml"
    empty.write_text("", encoding="utf-8")

    assert main_validation_logic.check_for_empty_file(empty) == 1


def test_check_for_empty_file_returns_zero_for_non_empty_file(tmp_path: Path) -> None:
    non_empty = tmp_path / "ok.yml"
    non_empty.write_text("name: build\n", encoding="utf-8")

    assert main_validation_logic.check_for_empty_file(non_empty) == 0


def test_check_for_empty_file_returns_one_on_os_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "broken.yml"
    yml_file.write_text("name: build\n", encoding="utf-8")

    def raise_os_error(self: Path) -> object:
        raise OSError("stat failed")

    monkeypatch.setattr(Path, "stat", raise_os_error, raising=False)

    assert main_validation_logic.check_for_empty_file(yml_file) == 1


def test_check_for_deprecated_keys_counts_multiple_hits(tmp_path: Path) -> None:
    content = "uses actions/setup-python@v3 and actions/checkout@v3"

    result = main_validation_logic.check_for_deprecated_keys(
        tmp_path / "wf.yml", content
    )

    assert result == 2


def test_check_for_deprecated_keys_returns_zero_for_empty_content(
    tmp_path: Path,
) -> None:
    result = main_validation_logic.check_for_deprecated_keys(tmp_path / "wf.yml", "")

    assert result == 0


def test_run_yq_returns_zero_for_base_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="ok\n", stderr=""
        )

    monkeypatch.setattr(main_validation_logic.subprocess, "run", fake_run)

    result = main_validation_logic.run_yq(
        yml_file, ".", "base syntax check", Path("yq")
    )

    assert result == 0


def test_run_yq_returns_one_for_missing_extended_field(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="null\n", stderr=""
        )

    monkeypatch.setattr(main_validation_logic.subprocess, "run", fake_run)

    result = main_validation_logic.run_yq(
        yml_file, ".jobs", "check '.jobs'", Path("yq")
    )

    assert result == 1


def test_run_yq_optional_missing_field_is_not_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="null\n", stderr=""
        )

    monkeypatch.setattr(main_validation_logic.subprocess, "run", fake_run)

    result = main_validation_logic.run_yq(
        yml_file, ".jobs[].needs", "check '.jobs[].needs'", Path("yq"), optional=True
    )

    assert result == 0


def test_run_yq_returns_one_on_subprocess_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("broken: [\n", encoding="utf-8")

    def raise_error(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1, cmd=args[0], stderr="parse error"
        )

    monkeypatch.setattr(main_validation_logic.subprocess, "run", raise_error)

    result = main_validation_logic.run_yq(
        yml_file, ".", "base syntax check", Path("yq")
    )

    assert result == 1


def test_check_indentation_returns_zero_for_clean_file(tmp_path: Path) -> None:
    yml_file = tmp_path / "clean.yml"
    yml_file.write_text("name: ci\njobs:\n  build:\n    steps: []\n", encoding="utf-8")

    assert main_validation_logic.check_indentation(yml_file) == 0


def test_check_indentation_detects_mixed_indent_error(tmp_path: Path) -> None:
    yml_file = tmp_path / "mixed.yml"
    yml_file.write_text("jobs:\n  \tbuild:\n", encoding="utf-8")

    assert main_validation_logic.check_indentation(yml_file) == 1


def test_check_indentation_tab_only_is_warning_not_error(tmp_path: Path) -> None:
    yml_file = tmp_path / "tab_only.yml"
    yml_file.write_text("jobs:\n\tbuild:\n", encoding="utf-8")

    assert main_validation_logic.check_indentation(yml_file) == 0


def test_check_indentation_ignores_blank_lines(tmp_path: Path) -> None:
    yml_file = tmp_path / "blank_lines.yml"
    yml_file.write_text("\n\nname: ci\n\n", encoding="utf-8")

    assert main_validation_logic.check_indentation(yml_file) == 0


def test_validate_config_raises_type_error_for_non_path() -> None:
    with pytest.raises(TypeError):
        main_validation_logic.validate_config("not_a_path", Path("yq"))


def test_validate_config_returns_zero_when_no_yaml_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(main_validation_logic, "_collect_yaml_files", lambda _: [])

    result = main_validation_logic.validate_config(tmp_path, Path("yq"))

    assert result == 0


def test_validate_config_returns_one_when_any_error_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda _: [yml_file]
    )
    monkeypatch.setattr(main_validation_logic, "check_for_empty_file", lambda _: 0)
    monkeypatch.setattr(main_validation_logic, "run_yq", lambda **_: 1)
    monkeypatch.setattr(
        main_validation_logic, "check_for_deprecated_keys", lambda *_: 0
    )
    monkeypatch.setattr(main_validation_logic, "check_indentation", lambda _: 0)

    result = main_validation_logic.validate_config(tmp_path, Path("yq"))

    assert result == 1


def test_validate_config_returns_zero_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda _: [yml_file]
    )
    monkeypatch.setattr(main_validation_logic, "check_for_empty_file", lambda _: 0)
    monkeypatch.setattr(main_validation_logic, "run_yq", lambda **_: 0)
    monkeypatch.setattr(
        main_validation_logic, "check_for_deprecated_keys", lambda *_: 0
    )
    monkeypatch.setattr(main_validation_logic, "check_indentation", lambda _: 0)

    result = main_validation_logic.validate_config(tmp_path, Path("yq"))

    assert result == 0


def test_run_yq_in_threadpool_includes_optional_checks_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(main_validation_logic, "EXTENDED_CHECKS", [".name"])
    monkeypatch.setattr(main_validation_logic, "OPTIONAL_CHECKS", [".jobs[].needs"])

    calls: list[tuple[str, bool]] = []

    def fake_run_yq(*, fpath, expression, description, yq_exec, optional=False):
        calls.append((expression, optional))
        return 0

    monkeypatch.setattr(main_validation_logic, "run_yq", fake_run_yq)

    result = main_validation_logic.run_yq_in_threadpool(
        fpath=yml_file,
        yq_exec=Path("yq"),
        run_optional=True,
    )

    assert result == 0
    assert (".name", False) in calls
    assert (".jobs[].needs", True) in calls


def test_regular_validation_returns_one_when_validate_config_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(main_validation_logic, "validate_config", lambda **_: 1)
    monkeypatch.setattr(
        main_validation_logic,
        "build_dot_scheme",
        lambda **_: pytest.fail("build_dot_scheme must not run when validation fails"),
    )

    assert (
        main_validation_logic.regular_validation(
            cfg_files=yml_file,
            yq_exe=Path("yq"),
            yml2dot_exe=Path("yml2dot"),
        )
        == 1
    )


def test_build_dot_scheme_returns_none_for_empty_input() -> None:
    result = main_validation_logic.build_dot_scheme([], Path("yml2dot"))

    assert result is None


def test_build_dot_scheme_returns_none_on_dot_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    class FakePopen:
        def __init__(self) -> None:
            self.stdout = None

        def wait(self) -> int:
            return 0

    def fake_popen(*args, **kwargs) -> FakePopen:
        return FakePopen()

    def raise_dot_error(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1, cmd=args[0], stderr=b"dot failed"
        )

    monkeypatch.setattr(main_validation_logic.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(main_validation_logic.subprocess, "run", raise_dot_error)

    result = main_validation_logic.build_dot_scheme([yml_file], Path("yml2dot"))

    assert result is None


def test_build_dot_scheme_returns_last_png_path_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = tmp_path / "one.yml"
    second = tmp_path / "two.yml"
    first.write_text("name: one\n", encoding="utf-8")
    second.write_text("name: two\n", encoding="utf-8")

    class FakePopen:
        def __init__(self) -> None:
            self.stdout = SimpleNamespace()

        def wait(self) -> int:
            return 0

    def fake_popen(*args, **kwargs) -> FakePopen:
        return FakePopen()

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout=b"", stderr=b""
        )

    monkeypatch.setattr(main_validation_logic.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(main_validation_logic.subprocess, "run", fake_run)

    result = main_validation_logic.build_dot_scheme([first, second], Path("yml2dot"))

    assert result == second.with_suffix(".png")
