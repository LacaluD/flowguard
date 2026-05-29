import subprocess
from pathlib import Path

import pytest
import yaml

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


def test_build_job_scoped_validation_yaml_returns_none_on_parse_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic.yaml,
        "safe_load",
        lambda *_: (_ for _ in ()).throw(main_validation_logic.yaml.YAMLError("bad")),
    )

    assert (
        main_validation_logic._build_job_scoped_validation_yaml(
            cfg_file=yml_file, job_name="build"
        )
        is None
    )


def test_build_job_scoped_validation_yaml_returns_none_for_non_mapping_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(main_validation_logic.yaml, "safe_load", lambda *_: [1, 2, 3])

    assert (
        main_validation_logic._build_job_scoped_validation_yaml(
            cfg_file=yml_file, job_name="build"
        )
        is None
    )


def test_build_job_scoped_validation_yaml_returns_none_when_jobs_mapping_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic.yaml, "safe_load", lambda *_: {"name": "ci"}
    )

    assert (
        main_validation_logic._build_job_scoped_validation_yaml(
            cfg_file=yml_file, job_name="build"
        )
        is None
    )


def test_build_job_scoped_validation_yaml_returns_none_when_job_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic.yaml,
        "safe_load",
        lambda *_: {"name": "ci", "jobs": {"test": {}}},
    )

    assert (
        main_validation_logic._build_job_scoped_validation_yaml(
            cfg_file=yml_file, job_name="build"
        )
        is None
    )


def test_build_job_scoped_validation_yaml_success_with_quoted_on_key(
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text(
        'name: CI\n"on":\n  push:\n    branches: [main]\njobs:\n  build:\n    runs-on: ubuntu-latest\n',
        encoding="utf-8",
    )

    result = main_validation_logic._build_job_scoped_validation_yaml(
        cfg_file=yml_file, job_name="build"
    )

    assert result is not None
    content = result.read_text(encoding="utf-8")
    assert "on:" in content
    assert "jobs:" in content
    assert "build:" in content


def test_regular_validation_rejects_multiple_cfg_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first = tmp_path / "a.yml"
    second = tmp_path / "b.yml"
    first.write_text("name: a\n", encoding="utf-8")
    second.write_text("name: b\n", encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic,
        "_collect_yaml_files",
        lambda *_: pytest.fail("must not collect files when len(cfg_files) > 1"),
    )

    result = main_validation_logic.regular_validation(
        cfg_files=[first, second],
        yq_exe=Path("yq"),
        excluded_paths=[],
        yml2dot_exe=Path("yml2dot"),
    )

    assert result == 1


def test_regular_validation_job_mode_returns_one_when_job_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text(
        """
name: CI
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo build
""".strip() + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda *_: [yml_file]
    )
    monkeypatch.setattr(main_validation_logic, "validate_config", lambda **_: 1)
    monkeypatch.setattr(
        main_validation_logic,
        "build_dot_scheme",
        lambda **_: pytest.fail("build_dot_scheme must not run when validation fails"),
    )

    assert (
        main_validation_logic.regular_validation(
            cfg_files=[yml_file],
            yq_exe=Path("yq"),
            excluded_paths=[],
            yml2dot_exe=Path("yml2dot"),
            job_name="build",
        )
        == 1
    )


def test_regular_validation_supports_json_input_and_builds_diagram(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    json_file = tmp_path / "wf.json"
    json_file.write_text('{"name": "ci", "jobs": {"build": {}}}', encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda *_: [json_file]
    )
    monkeypatch.setattr(main_validation_logic, "validate_config", lambda **_: 0)

    captured: dict[str, object] = {}

    def fake_build_dot_scheme(
        *,
        cfg_files,
        yml2dot_exec: Path,
        job_name: str | None = None,
        output_format: str = "svg",
    ):
        captured["cfg_files"] = list(cfg_files)
        return json_file.with_suffix(".svg")

    monkeypatch.setattr(
        main_validation_logic, "build_dot_scheme", fake_build_dot_scheme
    )

    result = main_validation_logic.regular_validation(
        cfg_files=[json_file],
        yq_exe=Path("yq"),
        excluded_paths=[],
        yml2dot_exe=Path("yml2dot"),
    )

    assert result == 0
    assert captured["cfg_files"] == [json_file]


def test_validate_config_read_text_error_returns_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda *_: [yml_file]
    )
    monkeypatch.setattr(main_validation_logic, "check_for_empty_file", lambda _: 0)

    def raise_read_error(*args, **kwargs):
        raise OSError("cannot read")

    monkeypatch.setattr(Path, "read_text", raise_read_error, raising=False)

    assert (
        main_validation_logic.validate_config(tmp_path, Path("yq"), excluded_paths=[])
        == 1
    )


def test_regular_validation_returns_one_when_build_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(main_validation_logic, "validate_config", lambda **_: 0)
    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda *_: [yml_file]
    )
    monkeypatch.setattr(main_validation_logic, "build_dot_scheme", lambda **_: None)

    assert (
        main_validation_logic.regular_validation(
            cfg_files=[yml_file],
            yq_exe=Path("yq"),
            excluded_paths=[],
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
        main_validation_logic, "_collect_yaml_files", lambda *_: [yml_file]
    )
    monkeypatch.setattr(
        main_validation_logic,
        "build_dot_scheme",
        lambda **_: yml_file.with_suffix(".png"),
    )

    assert (
        main_validation_logic.regular_validation(
            cfg_files=[yml_file],
            yq_exe=Path("yq"),
            excluded_paths=[],
            yml2dot_exe=Path("yml2dot"),
        )
        == 0
    )


def test_regular_validation_job_mode_validates_selected_job_and_builds_job_graph(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text(
        """
name: CI
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo build
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo deploy
""".strip() + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda *_: [yml_file]
    )

    captured: dict[str, object] = {}

    def fake_validate_config(
        *, yml_path: Path, yq_exec: Path, excluded_paths, run_optional: bool = False
    ):
        payload = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        captured["validated_payload"] = payload
        captured["validated_path"] = yml_path
        captured["excluded_paths"] = excluded_paths
        captured["run_optional"] = run_optional
        return 0

    def fake_build_dot_scheme(
        *,
        cfg_files,
        yml2dot_exec: Path,
        job_name: str | None = None,
        output_format: str = "svg",
    ):
        captured["dot_cfg_files"] = cfg_files
        captured["dot_job_name"] = job_name
        return yml_file.with_name("wf.build.png")

    monkeypatch.setattr(main_validation_logic, "validate_config", fake_validate_config)
    monkeypatch.setattr(
        main_validation_logic, "build_dot_scheme", fake_build_dot_scheme
    )

    result = main_validation_logic.regular_validation(
        cfg_files=[yml_file],
        yq_exe=Path("yq"),
        excluded_paths=[],
        yml2dot_exe=Path("yml2dot"),
        run_optional=True,
        job_name="build",
    )

    assert result == 0
    assert captured["excluded_paths"] == []
    assert captured["run_optional"] is True
    assert captured["dot_cfg_files"] == [yml_file]
    assert captured["dot_job_name"] == "build"


def test_validate_config_supports_json_by_converting_to_yaml_for_yq(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    json_file = tmp_path / "wf.json"
    json_file.write_text('{"name": "ci", "jobs": {"build": {}}}', encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda *_: [json_file]
    )
    monkeypatch.setattr(main_validation_logic, "check_for_empty_file", lambda _: 0)

    seen: dict[str, Path] = {}

    def fake_run_yq(
        *,
        fpath: Path,
        expression: str,
        description: str,
        yq_exec: Path,
        optional: bool = False,
    ):
        seen["base"] = fpath
        assert fpath.suffix == ".yml"
        return 0

    def fake_pool(
        *, fpath: Path, yq_exec: Path, fending: str, run_optional: bool = True
    ):
        seen["pool"] = fpath
        assert fpath.suffix == ".yml"
        assert fending == ".json"
        return 0

    monkeypatch.setattr(main_validation_logic, "run_yq", fake_run_yq)
    monkeypatch.setattr(main_validation_logic, "run_yq_in_threadpool", fake_pool)
    monkeypatch.setattr(
        main_validation_logic, "check_for_deprecated_keys", lambda *_: 0
    )
    monkeypatch.setattr(
        main_validation_logic,
        "check_indentation",
        lambda *_: pytest.fail("indentation should not run for json"),
    )

    result = main_validation_logic.validate_config(
        json_file, Path("yq"), excluded_paths=[]
    )

    assert result == 0
    assert "base" in seen and "pool" in seen


def test_validate_config_supports_toml_by_converting_to_yaml_for_yq(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    toml_file = tmp_path / "wf.toml"
    toml_file.write_text('name = "ci"\n[jobs.build]\n', encoding="utf-8")

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda *_: [toml_file]
    )
    monkeypatch.setattr(main_validation_logic, "check_for_empty_file", lambda *_: 0)
    monkeypatch.setattr(
        main_validation_logic,
        "run_yq",
        lambda **kwargs: 0 if kwargs["fpath"].suffix == ".yml" else 1,
    )
    monkeypatch.setattr(
        main_validation_logic,
        "run_yq_in_threadpool",
        lambda **kwargs: 0 if kwargs["fpath"].suffix == ".yml" else 1,
    )
    monkeypatch.setattr(
        main_validation_logic, "check_for_deprecated_keys", lambda *_: 0
    )
    monkeypatch.setattr(
        main_validation_logic,
        "check_indentation",
        lambda *_: pytest.fail("indentation should not run for toml"),
    )

    result = main_validation_logic.validate_config(
        toml_file, Path("yq"), excluded_paths=[]
    )

    assert result == 0


def test_regular_validation_job_mode_returns_one_when_job_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text(
        """
name: CI
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo build
""".strip() + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main_validation_logic, "_collect_yaml_files", lambda *_: [yml_file]
    )
    monkeypatch.setattr(
        main_validation_logic,
        "validate_config",
        lambda **_: pytest.fail(
            "validate_config must not run when selected job is missing"
        ),
    )

    monkeypatch.setattr(
        main_validation_logic,
        "build_dot_scheme",
        lambda **_: pytest.fail(
            "build_dot_scheme must not run when selected job is missing"
        ),
    )

    result = main_validation_logic.regular_validation(
        cfg_files=[yml_file],
        yq_exe=Path("yq"),
        excluded_paths=[],
        yml2dot_exe=Path("yml2dot"),
        job_name="deploy",
    )

    assert result == 1
