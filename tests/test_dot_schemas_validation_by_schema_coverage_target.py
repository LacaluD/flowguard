from __future__ import annotations

import json
import subprocess
from pathlib import Path

import jsonschema
import pytest
import yaml

from src import dot_schemas
from src import validation_by_schema as vbs
from src.validation_by_schema import SchemaValidator

# dot_schemas._safe_job_filename


def test_safe_job_filename_success_keeps_allowed_chars() -> None:
    assert dot_schemas._safe_job_filename("build_job-1") == "build_job-1"


def test_safe_job_filename_failure_like_input_sanitizes_symbols() -> None:
    assert dot_schemas._safe_job_filename("build@job#1") == "build_job_1"


def test_safe_job_filename_edge_empty_string() -> None:
    assert dot_schemas._safe_job_filename("") == ""


# dot_schemas._build_selected_job_yaml


def test_build_selected_job_yaml_success_writes_scoped_yaml(tmp_path: Path) -> None:
    cfg = tmp_path / "wf.yml"
    cfg.write_text(
        "name: CI\njobs:\n  build:\n    runs-on: ubuntu-latest\n", encoding="utf-8"
    )

    out = dot_schemas._build_selected_job_yaml(cfg, "build")

    assert out is not None
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["jobs"]["build"]["runs-on"] == "ubuntu-latest"
    out.unlink(missing_ok=True)


def test_build_selected_job_yaml_failure_on_yaml_parse_error(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.yml"
    cfg.write_text("name: CI\n", encoding="utf-8")
    mocker.patch("src.dot_schemas.yaml.safe_load",
                 side_effect=yaml.YAMLError("bad"))

    result = dot_schemas._build_selected_job_yaml(cfg, "build")

    assert result is None


def test_build_selected_job_yaml_edge_when_job_view_extraction_fails(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.yml"
    cfg.write_text("name: CI\njobs:\n  build: {}\n", encoding="utf-8")
    mocker.patch("src.dot_schemas._extract_job_view",
                 side_effect=ValueError("no job"))

    result = dot_schemas._build_selected_job_yaml(cfg, "build")

    assert result is None


# dot_schemas._build_yaml_from_supported_config


def test_build_yaml_from_supported_config_success_serializes_loaded_data(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.json"
    cfg.write_text('{"name":"CI"}', encoding="utf-8")
    mocker.patch("src.dot_schemas._load_config_data",
                 return_value={"name": "CI"})

    out = dot_schemas._build_yaml_from_supported_config(cfg)

    assert out is not None
    assert yaml.safe_load(out.read_text(encoding="utf-8")) == {"name": "CI"}
    out.unlink(missing_ok=True)


def test_build_yaml_from_supported_config_failure_returns_none_on_loader_error(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.toml"
    cfg.write_text('name = "CI"\n', encoding="utf-8")
    mocker.patch("src.dot_schemas._load_config_data",
                 side_effect=RuntimeError("boom"))

    out = dot_schemas._build_yaml_from_supported_config(cfg)

    assert out is None


def test_build_yaml_from_supported_config_edge_supports_scalar_payload(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.json"
    cfg.write_text("1", encoding="utf-8")
    mocker.patch("src.dot_schemas._load_config_data", return_value=7)

    out = dot_schemas._build_yaml_from_supported_config(cfg)

    assert out is not None
    assert yaml.safe_load(out.read_text(encoding="utf-8")) == 7
    out.unlink(missing_ok=True)


# dot_schemas.build_dot_scheme


def test_build_dot_scheme_success_for_yaml_config(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.yml"
    cfg.write_text("name: ci\n", encoding="utf-8")

    def fake_run(cmd, *args, **kwargs):
        if str(cmd[0]) == "yml2dot":
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=b"digraph G {}", stderr=b""
            )
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=b"", stderr=b""
        )

    mocker.patch("src.dot_schemas.subprocess.run", side_effect=fake_run)

    out = dot_schemas.build_dot_scheme([cfg], Path("yml2dot"))

    assert out == cfg.with_suffix(".svg")


def test_build_dot_scheme_failure_when_json_conversion_returns_none(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.json"
    cfg.write_text('{"name":"ci"}', encoding="utf-8")
    mocker.patch(
        "src.dot_schemas._build_yaml_from_supported_config", return_value=None)

    out = dot_schemas.build_dot_scheme([cfg], Path("yml2dot"))

    assert out is None


def test_build_dot_scheme_edge_cleans_temp_input_when_job_build_fails(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.json"
    cfg.write_text('{"name":"ci"}', encoding="utf-8")

    converted = tmp_path / "converted.yml"
    converted.write_text("jobs:\n  build: {}\n", encoding="utf-8")
    selected = tmp_path / "selected.yml"
    selected.write_text("jobs:\n  build: {}\n", encoding="utf-8")

    mocker.patch(
        "src.dot_schemas._build_yaml_from_supported_config", return_value=converted
    )
    mocker.patch("src.dot_schemas._build_selected_job_yaml",
                 return_value=selected)

    def fake_run(cmd, *args, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout=b"", stderr=b"bad"
        )

    mocker.patch("src.dot_schemas.subprocess.run", side_effect=fake_run)

    out = dot_schemas.build_dot_scheme(
        [cfg], Path("yml2dot"), job_name="build")

    assert out is None
    assert not converted.exists()


# validation_by_schema._load_schema


def test_load_schema_success_with_yaml_schema(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yml"
    schema.write_text(
        "type: object\nproperties:\n  name:\n    type: string\n", encoding="utf-8"
    )

    loaded = vbs._load_schema(schema)

    assert loaded["type"] == "object"


def test_load_schema_failure_when_root_is_not_mapping(tmp_path: Path) -> None:
    schema = tmp_path / "schema.json"
    schema.write_text("[]", encoding="utf-8")

    with pytest.raises(jsonschema.SchemaError):
        vbs._load_schema(schema)


def test_load_schema_edge_with_json_schema(tmp_path: Path) -> None:
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    loaded = vbs._load_schema(schema)

    assert loaded == {"type": "object"}


# validation_by_schema._validate_single_yaml


def test_validate_single_yaml_success_for_yaml_instance(tmp_path: Path) -> None:
    cfg = tmp_path / "wf.yml"
    cfg.write_text("name: CI\n", encoding="utf-8")

    out = vbs._validate_single_yaml(
        cfg, {"type": "object", "required": ["name"]})

    assert out == 0


def test_validate_single_yaml_failure_for_unsupported_extension(tmp_path: Path) -> None:
    cfg = tmp_path / "wf.ini"
    cfg.write_text("name=CI\n", encoding="utf-8")

    out = vbs._validate_single_yaml(cfg, {"type": "object"})

    assert out == 1


def test_validate_single_yaml_edge_reports_json_parse_error(tmp_path: Path) -> None:
    cfg = tmp_path / "wf.json"
    cfg.write_text("{", encoding="utf-8")

    out = vbs._validate_single_yaml(cfg, {"type": "object"})

    assert out == 1


def test_validate_single_yaml_edge_reports_toml_parse_error(tmp_path: Path) -> None:
    cfg = tmp_path / "wf.toml"
    cfg.write_text('name = "CI\n', encoding="utf-8")

    out = vbs._validate_single_yaml(cfg, {"type": "object"})

    assert out == 1


# validation_by_schema.validate_against_schema


def test_validate_against_schema_success_all_files_valid(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.yml"
    schema = tmp_path / "schema.json"
    cfg.write_text("name: CI\n", encoding="utf-8")
    schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    mocker.patch("src.validation_by_schema._collect_yaml_files",
                 return_value=[cfg])
    mocker.patch("src.validation_by_schema.check_for_empty_file",
                 return_value=0)
    mocker.patch(
        "src.validation_by_schema._load_schema", return_value={"type": "object"}
    )
    mocker.patch("src.validation_by_schema._validate_single_yaml",
                 return_value=0)

    out = vbs.validate_against_schema(cfg, schema)

    assert out == 0


def test_validate_against_schema_failure_when_no_files_found(
    mocker,
    tmp_path: Path,
) -> None:
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    mocker.patch("src.validation_by_schema._collect_yaml_files",
                 return_value=[])

    out = vbs.validate_against_schema(tmp_path, schema)

    assert out == 1


def test_validate_against_schema_edge_skips_validation_after_empty_check_error(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.yml"
    schema = tmp_path / "schema.json"
    cfg.write_text("name: CI\n", encoding="utf-8")
    schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    mocker.patch("src.validation_by_schema._collect_yaml_files",
                 return_value=[cfg])
    mocker.patch("src.validation_by_schema.check_for_empty_file",
                 return_value=1)
    mocker.patch(
        "src.validation_by_schema._load_schema", return_value={"type": "object"}
    )
    validate_spy = mocker.patch(
        "src.validation_by_schema._validate_single_yaml", return_value=0
    )

    out = vbs.validate_against_schema(cfg, schema)

    assert out == 1
    validate_spy.assert_not_called()


# validation_by_schema.validate_custom_pipeline


def test_validate_custom_pipeline_success_returns_zero(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.yml"
    schema = tmp_path / "schema.json"
    cfg.write_text("name: CI\n", encoding="utf-8")
    schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    mocker.patch(
        "src.validation_by_schema.SchemaValidator.validate_against_schema", return_value=0)
    mocker.patch("src.validation_by_schema._collect_yaml_files",
                 return_value=[cfg])
    mocker.patch(
        "src.validation_by_schema.build_dot_scheme",
        return_value=cfg.with_suffix(".svg"),
    )

    out = SchemaValidator(schema).validate_custom_pipeline(
        cfg_files=[cfg], yml2dot_exe=Path("yml2dot")
    )

    assert out == 0


def test_validate_custom_pipeline_failure_when_schema_validation_fails(
    mocker,
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "wf.yml"
    schema = tmp_path / "schema.json"
    cfg.write_text("name: CI\n", encoding="utf-8")
    schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    mocker.patch(
        "src.validation_by_schema.SchemaValidator.validate_against_schema", return_value=1)

    out = SchemaValidator(schema).validate_custom_pipeline(
        cfg_files=[cfg], yml2dot_exe=Path("yml2dot")
    )

    assert out == 1


def test_validate_custom_pipeline_edge_empty_cfg_files_returns_one(
    tmp_path: Path,
) -> None:
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    out = SchemaValidator(schema).validate_custom_pipeline(
        cfg_files=[], yml2dot_exe=Path("yml2dot")
    )

    assert out == 1
