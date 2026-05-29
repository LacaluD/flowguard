from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from src import dot_schemas
from src import validation_by_schema

# dot_schemas._safe_job_filename


def test_safe_job_filename_success_keeps_alnum_dash_underscore() -> None:
    assert dot_schemas._safe_job_filename("build_job-1") == "build_job-1"


def test_safe_job_filename_failure_like_symbols_are_sanitized() -> None:
    assert dot_schemas._safe_job_filename("job@prod#1") == "job_prod_1"


def test_safe_job_filename_edge_empty_string_returns_empty() -> None:
    assert dot_schemas._safe_job_filename("") == ""


# dot_schemas._build_selected_job_yaml


def test_build_selected_job_yaml_success_returns_temp_yaml(tmp_path: Path) -> None:
    src = tmp_path / "wf.yml"
    src.write_text(
        "name: CI\njobs:\n  build:\n    runs-on: ubuntu-latest\n", encoding="utf-8"
    )

    out = dot_schemas._build_selected_job_yaml(src, "build")

    assert out is not None
    payload = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert payload["jobs"]["build"]["runs-on"] == "ubuntu-latest"
    out.unlink(missing_ok=True)


def test_build_selected_job_yaml_failure_when_yaml_parse_fails(
    mocker,
    tmp_path: Path,
) -> None:
    src = tmp_path / "wf.yml"
    src.write_text("name: CI\n", encoding="utf-8")
    mocker.patch("src.dot_schemas.yaml.safe_load", side_effect=yaml.YAMLError("bad"))

    out = dot_schemas._build_selected_job_yaml(src, "build")

    assert out is None


def test_build_selected_job_yaml_edge_when_extract_job_view_fails(
    mocker,
    tmp_path: Path,
) -> None:
    src = tmp_path / "wf.yml"
    src.write_text("name: CI\njobs:\n  build: {}\n", encoding="utf-8")
    mocker.patch("src.dot_schemas._extract_job_view", side_effect=ValueError("missing"))

    out = dot_schemas._build_selected_job_yaml(src, "build")

    assert out is None


# dot_schemas._build_yaml_from_supported_config


def test_build_yaml_from_supported_config_success_writes_yaml(
    mocker,
    tmp_path: Path,
) -> None:
    src = tmp_path / "wf.json"
    src.write_text('{"name":"CI"}', encoding="utf-8")
    mocker.patch("src.dot_schemas._load_config_data", return_value={"name": "CI"})

    out = dot_schemas._build_yaml_from_supported_config(src)

    assert out is not None
    assert yaml.safe_load(out.read_text(encoding="utf-8")) == {"name": "CI"}
    out.unlink(missing_ok=True)


def test_build_yaml_from_supported_config_failure_returns_none(
    mocker,
    tmp_path: Path,
) -> None:
    src = tmp_path / "wf.toml"
    src.write_text('name = "CI"\n', encoding="utf-8")
    mocker.patch("src.dot_schemas._load_config_data", side_effect=RuntimeError("boom"))

    out = dot_schemas._build_yaml_from_supported_config(src)

    assert out is None


def test_build_yaml_from_supported_config_edge_supports_scalar_payload(
    mocker,
    tmp_path: Path,
) -> None:
    src = tmp_path / "wf.json"
    src.write_text("1", encoding="utf-8")
    mocker.patch("src.dot_schemas._load_config_data", return_value=7)

    out = dot_schemas._build_yaml_from_supported_config(src)

    assert out is not None
    assert yaml.safe_load(out.read_text(encoding="utf-8")) == 7
    out.unlink(missing_ok=True)


# dot_schemas.build_dot_scheme


def test_build_dot_scheme_failure_when_json_conversion_returns_none(
    mocker,
    tmp_path: Path,
) -> None:
    src = tmp_path / "wf.json"
    src.write_text('{"name":"CI"}', encoding="utf-8")
    mocker.patch("src.dot_schemas._build_yaml_from_supported_config", return_value=None)

    out = dot_schemas.build_dot_scheme([src], Path("yml2dot"))

    assert out is None


def test_build_dot_scheme_edge_unlinks_temp_when_job_extract_fails(
    mocker,
    tmp_path: Path,
) -> None:
    src = tmp_path / "wf.json"
    src.write_text('{"name":"CI"}', encoding="utf-8")
    converted = tmp_path / "converted.yml"
    converted.write_text("name: CI\n", encoding="utf-8")

    mocker.patch(
        "src.dot_schemas._build_yaml_from_supported_config", return_value=converted
    )
    mocker.patch("src.dot_schemas._build_selected_job_yaml", return_value=None)

    out = dot_schemas.build_dot_scheme([src], Path("yml2dot"), job_name="build")

    assert out is None
    assert not converted.exists()


def test_build_dot_scheme_edge_replaces_temp_input_for_job_scope(
    mocker,
    tmp_path: Path,
) -> None:
    src = tmp_path / "wf.json"
    src.write_text('{"name":"CI"}', encoding="utf-8")

    converted = tmp_path / "converted.yml"
    converted.write_text("jobs:\n  build: {}\n", encoding="utf-8")
    selected = tmp_path / "selected.yml"
    selected.write_text("jobs:\n  build: {}\n", encoding="utf-8")

    mocker.patch(
        "src.dot_schemas._build_yaml_from_supported_config", return_value=converted
    )
    mocker.patch("src.dot_schemas._build_selected_job_yaml", return_value=selected)

    def fake_run(cmd, *args, **kwargs):
        if cmd[0] == "yml2dot":
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout=b"", stderr=b"bad"
            )
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=b"", stderr=b""
        )

    mocker.patch("src.dot_schemas.subprocess.run", side_effect=fake_run)

    out = dot_schemas.build_dot_scheme([src], Path("yml2dot"), job_name="build")

    assert out is None
    assert not converted.exists()


# validation_by_schema._validate_single_yaml


def test_validate_single_yaml_failure_on_unsupported_extension(
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.ini"
    cfg.write_text("name=CI\n", encoding="utf-8")

    out = validation_by_schema._validate_single_yaml(cfg, {"type": "object"})

    assert out == 1


def test_validate_single_yaml_failure_on_json_parse_error(
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.json"
    cfg.write_text("{", encoding="utf-8")

    out = validation_by_schema._validate_single_yaml(cfg, {"type": "object"})

    assert out == 1


def test_validate_single_yaml_failure_on_toml_parse_error(
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.toml"
    cfg.write_text('name = "CI\n', encoding="utf-8")

    out = validation_by_schema._validate_single_yaml(cfg, {"type": "object"})

    assert out == 1


# validation_by_schema.validate_custom_pipeline


def test_validate_custom_pipeline_failure_on_empty_cfg_files(
    tmp_path: Path,
) -> None:
    out = validation_by_schema.validate_custom_pipeline(
        cfg_files=[],
        val_schema=tmp_path / "schema.json",
        yml2dot_exe=Path("yml2dot"),
    )

    assert out == 1
