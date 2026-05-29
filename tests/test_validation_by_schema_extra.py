import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from src import validation_by_schema


def test_load_schema_non_mapping_raises_schema_error(tmp_path: Path) -> None:
    s = tmp_path / "schema.json"
    s.write_text("[]", encoding="utf-8")

    with pytest.raises(jsonschema.SchemaError):
        validation_by_schema._load_schema(s)


def test_validate_single_yaml_handles_os_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    f = tmp_path / "wf.yml"
    f.write_text("name: ci\n", encoding="utf-8")

    def raise_os_error(*args, **kwargs):
        raise OSError("read failed")

    monkeypatch.setattr(Path, "read_text", raise_os_error, raising=False)

    assert validation_by_schema._validate_single_yaml(f, {"type": "object"}) == 1


def test_validate_against_schema_handles_json_parse_error(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    yaml_file = tmp_path / "wf.yml"
    schema_file.write_text("{", encoding="utf-8")
    yaml_file.write_text("name: CI\n", encoding="utf-8")

    assert validation_by_schema.validate_against_schema(yaml_file, schema_file) == 1


def test_validate_against_schema_handles_yaml_parse_error(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.yaml"
    yaml_file = tmp_path / "wf.yml"
    schema_file.write_text("type: [", encoding="utf-8")
    yaml_file.write_text("name: CI\n", encoding="utf-8")

    assert validation_by_schema.validate_against_schema(yaml_file, schema_file) == 1


def test_validate_against_schema_returns_one_when_schema_file_missing(
    tmp_path: Path,
) -> None:
    yaml_file = tmp_path / "wf.yml"
    yaml_file.write_text("name: CI\n", encoding="utf-8")
    missing_schema = tmp_path / "missing_schema.json"

    assert validation_by_schema.validate_against_schema(yaml_file, missing_schema) == 1


def test_validate_against_schema_handles_schema_file_os_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schema_file = tmp_path / "schema.json"
    yaml_file = tmp_path / "wf.yml"
    schema_file.write_text("{}", encoding="utf-8")
    yaml_file.write_text("name: CI\n", encoding="utf-8")

    def raise_os_error(*args, **kwargs):
        raise OSError("cannot read schema")

    monkeypatch.setattr(validation_by_schema, "_load_schema", raise_os_error)

    assert validation_by_schema.validate_against_schema(yaml_file, schema_file) == 1


def test_validate_against_schema_handles_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schema_file = tmp_path / "schema.json"
    yaml_file = tmp_path / "wf.yml"
    schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    yaml_file.write_text("name: CI\n", encoding="utf-8")

    monkeypatch.setattr(
        validation_by_schema, "_collect_yaml_files", lambda _: [yaml_file]
    )
    monkeypatch.setattr(
        validation_by_schema, "_load_schema", lambda _: {"type": "object"}
    )
    monkeypatch.setattr(validation_by_schema, "check_for_empty_file", lambda _: 0)

    def raise_unexpected(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(validation_by_schema, "_validate_single_yaml", raise_unexpected)

    assert validation_by_schema.validate_against_schema(yaml_file, schema_file) == 1


def test_validate_custom_pipeline_returns_one_when_diagram_build_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    schema_file = tmp_path / "schema.json"
    yml_file.write_text("name: ci\n", encoding="utf-8")
    schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    monkeypatch.setattr(validation_by_schema, "validate_against_schema", lambda **_: 0)
    monkeypatch.setattr(
        validation_by_schema, "_collect_yaml_files", lambda _: [yml_file]
    )
    monkeypatch.setattr(validation_by_schema, "build_dot_scheme", lambda **_: None)

    assert (
        validation_by_schema.validate_custom_pipeline(
            cfg_files=[yml_file],
            val_schema=schema_file,
            yml2dot_exe=Path("yml2dot"),
        )
        == 1
    )


def test_validate_custom_pipeline_returns_one_when_schema_validation_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    schema_file = tmp_path / "schema.json"
    yml_file.write_text("name: ci\n", encoding="utf-8")
    schema_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(validation_by_schema, "validate_against_schema", lambda **_: 1)

    assert (
        validation_by_schema.validate_custom_pipeline(
            cfg_files=[yml_file],
            val_schema=schema_file,
            yml2dot_exe=Path("yml2dot"),
        )
        == 1
    )


def test_validate_custom_pipeline_returns_zero_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "wf.yml"
    schema_file = tmp_path / "schema.json"
    yml_file.write_text("name: ci\n", encoding="utf-8")
    schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    monkeypatch.setattr(validation_by_schema, "validate_against_schema", lambda **_: 0)
    monkeypatch.setattr(
        validation_by_schema, "_collect_yaml_files", lambda _: [yml_file]
    )
    monkeypatch.setattr(
        validation_by_schema,
        "build_dot_scheme",
        lambda **_: yml_file.with_suffix(".png"),
    )

    assert (
        validation_by_schema.validate_custom_pipeline(
            cfg_files=[yml_file],
            val_schema=schema_file,
            yml2dot_exe=Path("yml2dot"),
        )
        == 0
    )


def test_validate_custom_pipeline_returns_one_when_multiple_cfg_files_passed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = tmp_path / "a.yml"
    second = tmp_path / "b.yml"
    first.write_text("name: a\n", encoding="utf-8")
    second.write_text("name: b\n", encoding="utf-8")

    monkeypatch.setattr(
        validation_by_schema,
        "validate_against_schema",
        lambda **_: pytest.fail("schema validation must not run for multiple files"),
    )
    monkeypatch.setattr(
        validation_by_schema,
        "build_dot_scheme",
        lambda **_: pytest.fail("diagram generation must not run for multiple files"),
    )

    assert (
        validation_by_schema.validate_custom_pipeline(
            cfg_files=[first, second],
            val_schema=tmp_path / "schema.json",
            yml2dot_exe=Path("yml2dot"),
        )
        == 1
    )
