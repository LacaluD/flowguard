from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from src import pipeline as mvl


def test_materialize_yaml_for_validation_success_writes_temp_yaml(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    src_file = tmp_path / "config.json"
    src_file.write_text('{"name":"ci"}', encoding="utf-8")

    monkeypatch.setattr(mvl, "_load_config_data", lambda _: {"name": "ci", "jobs": {}})

    out = mvl._materialize_yaml_for_validation(src_file)

    assert out.exists()
    assert out.suffix == ".yml"
    loaded = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert loaded == {"name": "ci", "jobs": {}}
    out.unlink(missing_ok=True)


def test_materialize_yaml_for_validation_failure_propagates_loader_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    src_file = tmp_path / "bad.toml"
    src_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        mvl,
        "_load_config_data",
        lambda _: (_ for _ in ()).throw(ValueError("unsupported")),
    )

    with pytest.raises(ValueError, match="unsupported"):
        mvl._materialize_yaml_for_validation(src_file)


def test_materialize_yaml_for_validation_edge_allows_scalar_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    src_file = tmp_path / "scalar.json"
    src_file.write_text("1", encoding="utf-8")

    monkeypatch.setattr(mvl, "_load_config_data", lambda _: 42)

    out = mvl._materialize_yaml_for_validation(src_file)

    assert yaml.safe_load(out.read_text(encoding="utf-8")) == 42
    out.unlink(missing_ok=True)


# _normalize_action_ref


def test_normalize_action_ref_success_strips_quotes_and_v() -> None:
    assert mvl._normalize_action_ref('"actions/checkout@v3"') == (
        "actions/checkout",
        "3",
    )


def test_normalize_action_ref_failure_without_at_returns_none() -> None:
    assert mvl._normalize_action_ref("actions/checkout") is None


def test_normalize_action_ref_edge_empty_version_after_v_returns_none() -> None:
    assert mvl._normalize_action_ref("actions/checkout@v") is None


# check_for_deprecated_keys


def test_check_for_deprecated_keys_success_counts_hits(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mvl, "DEPRECATED_ACTIONS", ["actions/checkout@v3"])

    got = mvl.check_for_deprecated_keys(tmp_path / "wf.yml", "uses: actions/checkout@3")

    assert got == 1


def test_check_for_deprecated_keys_failure_empty_content_is_zero(
    tmp_path: Path,
) -> None:
    assert mvl.check_for_deprecated_keys(tmp_path / "wf.yml", "") == 0


def test_check_for_deprecated_keys_edge_ignores_invalid_deprecated_entries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mvl, "DEPRECATED_ACTIONS", ["invalid-entry"])

    got = mvl.check_for_deprecated_keys(
        tmp_path / "wf.yml", "uses: actions/setup-python@v5"
    )

    assert got == 0


# run_yq


def test_run_yq_success_base_expression_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(mvl, "count_timeout", lambda **_: 7)

    def fake_run(*args, **kwargs):
        assert kwargs["timeout"] == 7
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="ok\n", stderr=""
        )

    monkeypatch.setattr(mvl.subprocess, "run", fake_run)

    assert mvl.run_yq(f, ".", "base", Path("yq")) == 0


def test_run_yq_failure_called_process_error_logs_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(mvl, "count_timeout", lambda **_: 5)

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=args[0], stderr="boom")

    monkeypatch.setattr(mvl.subprocess, "run", fake_run)

    assert mvl.run_yq(f, ".jobs", "check", Path("yq")) == 1


def test_run_yq_edge_optional_missing_field_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(mvl, "count_timeout", lambda **_: 1)
    monkeypatch.setattr(
        mvl.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="null\n", stderr=""
        ),
    )

    assert mvl.run_yq(f, ".jobs[].needs", "optional", Path("yq"), optional=True) == 0


# check_indentation


def test_check_indentation_success_clean_file_returns_zero(tmp_path: Path) -> None:
    f = tmp_path / "clean.yml"
    f.write_text("name: ci\njobs:\n  build:\n    steps: []\n", encoding="utf-8")

    assert mvl.check_indentation(f) == 0


def test_check_indentation_failure_mixed_tabs_spaces_counts_error(
    tmp_path: Path,
) -> None:
    f = tmp_path / "mixed.yml"
    f.write_text("jobs:\n  \tbuild:\n", encoding="utf-8")

    assert mvl.check_indentation(f) == 1


def test_check_indentation_edge_tab_and_trailing_spaces_are_warnings_only(
    tmp_path: Path,
) -> None:
    f = tmp_path / "warn.yml"
    f.write_text("jobs:\n\tbuild:  \n", encoding="utf-8")

    assert mvl.check_indentation(f) == 0


# validate_config


def test_validate_config_success_yaml_flow_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")
    pipeline = mvl.ValidationPipeline(
        yq_exe=Path("yq"), excluded_paths=[], run_optional=False
    )

    monkeypatch.setattr(mvl, "_collect_yaml_files", lambda *_: [f])
    monkeypatch.setattr(mvl, "check_for_empty_file", lambda *_: 0)
    monkeypatch.setattr(pipeline, "run_yq", lambda **_: 0)
    monkeypatch.setattr(pipeline, "run_yq_in_threadpool", lambda **_: 0)
    monkeypatch.setattr(pipeline, "check_for_deprecated_keys", lambda *_: 0)
    monkeypatch.setattr(pipeline, "check_indentation", lambda *_: 0)

    assert pipeline.validate_config(f) == 0


def test_validate_config_failure_non_path_raises_type_error() -> None:
    with pytest.raises(TypeError):
        mvl.validate_config("not-path", Path("yq"), excluded_paths=[])


def test_validate_config_edge_json_conversion_exception_adds_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.json"
    f.write_text('{"name":"ci"}', encoding="utf-8")

    monkeypatch.setattr(mvl, "_collect_yaml_files", lambda *_: [f])
    monkeypatch.setattr(mvl, "check_for_empty_file", lambda *_: 0)
    monkeypatch.setattr(
        mvl,
        "_materialize_yaml_for_validation",
        lambda *_: (_ for _ in ()).throw(RuntimeError("convert-fail")),
    )
    monkeypatch.setattr(mvl, "check_for_deprecated_keys", lambda *_: 0)
    monkeypatch.setattr(mvl, "check_indentation", lambda *_: 0)

    assert mvl.validate_config(f, Path("yq"), excluded_paths=[]) == 1


# run_yq_in_threadpool


def test_run_yq_in_threadpool_success_all_checks_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(mvl, "EXTENDED_CHECKS", [".name", ".jobs"])
    monkeypatch.setattr(mvl, "OPTIONAL_CHECKS", [".jobs[].needs"])
    monkeypatch.setattr(mvl.ValidationPipeline, "run_yq", lambda self, **_: 0)

    validator = mvl.ValidationPipeline(
        yq_exe=Path("yq"),
        excluded_paths=[],
        run_optional=True,
    )
    assert validator.run_yq_in_threadpool(fpath=f, fending=".json") == 0


def test_run_yq_in_threadpool_failure_accumulates_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")
    pipeline = mvl.ValidationPipeline(
        yq_exe=Path("yq"), excluded_paths=[], run_optional=False
    )

    monkeypatch.setattr(mvl, "EXTENDED_CHECKS", ["ok", "bad"])
    monkeypatch.setattr(mvl, "OPTIONAL_CHECKS", [])

    def fake_run_yq(*, expression: str, **kwargs):
        return 1 if expression == "bad" else 0

    monkeypatch.setattr(pipeline, "run_yq", fake_run_yq)

    assert pipeline.run_yq_in_threadpool(f, fending=".json") == 1


def test_run_yq_in_threadpool_edge_skips_optional_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")
    pipeline = mvl.ValidationPipeline(
        yq_exe=Path("yq"), excluded_paths=[], run_optional=False
    )

    monkeypatch.setattr(mvl, "EXTENDED_CHECKS", [".name"])
    monkeypatch.setattr(mvl, "OPTIONAL_CHECKS", [".optional"])
    seen: list[str] = []

    def fake_run_yq(*, expression: str, **kwargs):
        seen.append(expression)
        return 0

    monkeypatch.setattr(pipeline, "run_yq", fake_run_yq)

    assert pipeline.run_yq_in_threadpool(f, fending=".json") == 0
    assert seen == [".name"]


# _build_job_scoped_validation_yaml


def test_build_job_scoped_validation_yaml_success_with_on_key(tmp_path: Path) -> None:
    f = tmp_path / "wf.yml"
    f.write_text(
        "name: CI\non:\n  push: {}\njobs:\n  build:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )

    out = mvl._build_job_scoped_validation_yaml(f, "build")

    assert out is not None
    payload = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert payload["name"] == "CI"
    assert "on" in payload
    assert "build" in payload["jobs"]
    out.unlink(missing_ok=True)


def test_build_job_scoped_validation_yaml_failure_parse_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(
        mvl,
        "_load_config_data",
        lambda *_: (_ for _ in ()).throw(ValueError("bad parse")),
    )

    assert mvl._build_job_scoped_validation_yaml(f, "build") is None


def test_build_job_scoped_validation_yaml_edge_uses_bool_true_as_on(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")

    monkeypatch.setattr(
        mvl,
        "_load_config_data",
        lambda *_: {"name": "CI", True: {"push": {}}, "jobs": {"build": {}}},
    )

    out = mvl._build_job_scoped_validation_yaml(f, "build")

    assert out is not None
    payload = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert payload["on"] == {"push": {}}
    out.unlink(missing_ok=True)


# regular_validation


def test_regular_validation_success_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")
    pipeline = mvl.ValidationPipeline(
        yq_exe=Path("yq"), excluded_paths=[], run_optional=False
    )

    monkeypatch.setattr(mvl, "_collect_yaml_files", lambda *_: [f])
    monkeypatch.setattr(pipeline, "validate_config", lambda **_: 0)
    monkeypatch.setattr(mvl, "build_dot_scheme", lambda **_: f.with_suffix(".svg"))

    assert pipeline.regular_validation(cfg_files=[f], yml2dot_exe=Path("yml2dot")) == 0


def test_regular_validation_failure_empty_cfg_files_returns_one() -> None:
    assert (
        mvl.regular_validation(
            cfg_files=[],
            yq_exe=Path("yq"),
            excluded_paths=[],
            yml2dot_exe=Path("yml2dot"),
        )
        == 1
    )


def test_regular_validation_edge_job_mode_failure_cleans_temp_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\njobs:\n  build: {}\n", encoding="utf-8")
    pipeline = mvl.ValidationPipeline(
        yq_exe=Path("yq"), excluded_paths=[], run_optional=False
    )

    temp_job = tmp_path / "job-temp.yml"
    temp_job.write_text("jobs:\n  build: {}\n", encoding="utf-8")

    monkeypatch.setattr(mvl, "_collect_yaml_files", lambda *_: [f])
    monkeypatch.setattr(
        pipeline, "_build_job_scoped_validation_yaml", lambda **_: temp_job
    )
    monkeypatch.setattr(pipeline, "validate_config", lambda **_: 1)

    assert (
        pipeline.regular_validation(
            cfg_files=[f],
            yml2dot_exe=Path("yml2dot"),
            job_name="build",
        )
        == 1
    )
    assert not temp_job.exists()
