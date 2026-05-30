import json
from pathlib import Path

import jsonschema
import pytest

from src import validation_by_schema as vbs
from src.validation_by_schema import SchemaValidator


# schema_validator = SchemaValidator()
def _write_json_schema(schema_path: Path) -> None:
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "jobs": {"type": "object"},
        },
    }
    schema_path.write_text(json.dumps(schema), encoding="utf-8")


def _write_yaml_schema(schema_path: Path) -> None:
    schema_path.write_text(
        "type: object\nrequired:\n  - name\nproperties:\n  name:\n    type: string\n",
        encoding="utf-8",
    )


def _validator(schema_file: Path) -> SchemaValidator:
    return SchemaValidator(schema_file)


def test_validate_against_schema_valid_schema_and_yaml_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schema_file = tmp_path / "schema.json"
    yaml_file = tmp_path / "workflow.yml"

    _write_json_schema(schema_file)
    yaml_file.write_text("name: CI\njobs: {}\n", encoding="utf-8")
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [yaml_file])
    schema_validator = _validator(schema_file)

    result = schema_validator.validate_against_schema(yml_path=yaml_file)

    assert result == 0


def test_validate_against_schema_valid_schema_and_json_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schema_file = tmp_path / "schema.json"
    json_file = tmp_path / "workflow.json"

    _write_json_schema(schema_file)
    json_file.write_text('{"name": "CI", "jobs": {}}', encoding="utf-8")
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [json_file])
    schema_validator = _validator(schema_file)

    result = schema_validator.validate_against_schema(yml_path=json_file)

    assert result == 0


def test_validate_against_schema_valid_schema_and_toml_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schema_file = tmp_path / "schema.json"
    toml_file = tmp_path / "workflow.toml"

    _write_json_schema(schema_file)
    toml_file.write_text('name = "CI"\n[jobs]\n', encoding="utf-8")
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [toml_file])
    schema_validator = _validator(schema_file)

    result = schema_validator.validate_against_schema(yml_path=toml_file)

    assert result == 0


def test_load_schema_accepts_yaml_schema(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.yml"
    _write_yaml_schema(schema_file)

    loaded = _validator(schema_file)._load_schema(schema_file)

    assert loaded["type"] == "object"
    assert loaded["properties"]["name"]["type"] == "string"


def test_load_schema_rejects_non_mapping_schema(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    schema_file.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(jsonschema.SchemaError):
        _validator(schema_file)._load_schema(schema_file)


def test_validate_single_yaml_returns_zero_for_valid_yaml(tmp_path: Path) -> None:
    schema = {"type": "object", "required": ["name"]}
    yaml_file = tmp_path / "workflow.yml"
    yaml_file.write_text("name: CI\n", encoding="utf-8")

    assert _validator(
        tmp_path / "schema.json")._validate_single_yaml(yaml_file, schema) == 0


def test_validate_single_yaml_returns_one_for_validation_error(
    tmp_path: Path,
) -> None:
    schema = {"type": "object", "required": ["name"]}
    yaml_file = tmp_path / "workflow.yml"
    yaml_file.write_text("jobs: {}\n", encoding="utf-8")

    assert _validator(
        tmp_path / "schema.json")._validate_single_yaml(yaml_file, schema) == 1


def test_validate_single_yaml_returns_one_for_yaml_parse_error(
    tmp_path: Path,
) -> None:
    schema = {"type": "object"}
    yaml_file = tmp_path / "broken.yml"
    yaml_file.write_text("name: [\n", encoding="utf-8")

    assert _validator(
        tmp_path / "schema.json")._validate_single_yaml(yaml_file, schema) == 1


def test_validate_single_yaml_returns_one_on_read_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schema = {"type": "object"}
    yaml_file = tmp_path / "broken.yml"
    yaml_file.write_text("name: CI\n", encoding="utf-8")

    def raise_read_error(*args, **kwargs):
        raise OSError("cannot read")

    monkeypatch.setattr(Path, "read_text", raise_read_error, raising=False)

    assert _validator(
        tmp_path / "schema.json")._validate_single_yaml(yaml_file, schema) == 1


def test_validate_against_schema_invalid_schema_returns_one(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    yaml_file = tmp_path / "workflow.yml"

    schema_file.write_text(
        '{"type": "object", "properties": "broken"}', encoding="utf-8"
    )
    yaml_file.write_text("name: CI\n", encoding="utf-8")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [yaml_file])
    try:
        result = _validator(schema_file).validate_against_schema(
            yml_path=yaml_file)
    finally:
        monkeypatch.undo()

    assert result == 1


def test_validate_against_schema_invalid_yaml_returns_one(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    yaml_file = tmp_path / "workflow.yml"

    _write_json_schema(schema_file)
    yaml_file.write_text("name: [\n", encoding="utf-8")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [yaml_file])
    try:
        result = _validator(schema_file).validate_against_schema(
            yml_path=yaml_file)
    finally:
        monkeypatch.undo()

    assert result == 1


def test_validate_against_schema_directory_with_multiple_files_returns_one_on_any_invalid(
    tmp_path: Path,
) -> None:
    schema_file = tmp_path / "schema.json"
    yml_dir = tmp_path / "yamls"
    yml_dir.mkdir()

    valid_file = yml_dir / "good.yml"
    invalid_file = yml_dir / "bad.yaml"

    _write_json_schema(schema_file)
    valid_file.write_text("name: CI\n", encoding="utf-8")
    invalid_file.write_text("jobs: {}\n", encoding="utf-8")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        vbs, "_collect_yaml_files", lambda *_: [valid_file, invalid_file]
    )
    try:
        result = _validator(schema_file).validate_against_schema(
            yml_path=yml_dir)
    finally:
        monkeypatch.undo()

    assert result == 1


def test_validate_against_schema_empty_directory_returns_one(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    _write_json_schema(schema_file)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [])
    try:
        result = _validator(schema_file).validate_against_schema(
            yml_path=empty_dir)
    finally:
        monkeypatch.undo()

    assert result == 1


def test_validate_against_schema_empty_yaml_file_returns_one(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    empty_yaml = tmp_path / "empty.yml"

    _write_json_schema(schema_file)
    empty_yaml.write_text("", encoding="utf-8")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [empty_yaml])
    try:
        result = _validator(schema_file).validate_against_schema(
            yml_path=empty_yaml)
    finally:
        monkeypatch.undo()

    assert result == 1


def test_validate_against_schema_returns_one_when_schema_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yaml_file = tmp_path / "workflow.yml"
    yaml_file.write_text("name: CI\n", encoding="utf-8")
    schema_file = tmp_path / "missing.json"

    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [yaml_file])

    result = _validator(schema_file).validate_against_schema(
        yml_path=yaml_file)

    assert result == 1


def test_validate_against_schema_returns_one_on_schema_json_parse_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yaml_file = tmp_path / "workflow.yml"
    schema_file = tmp_path / "schema.json"
    yaml_file.write_text("name: CI\n", encoding="utf-8")
    schema_file.write_text("{broken json", encoding="utf-8")

    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [yaml_file])

    result = _validator(schema_file).validate_against_schema(
        yml_path=yaml_file)

    assert result == 1


def test_validate_against_schema_returns_one_on_schema_yaml_parse_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yaml_file = tmp_path / "workflow.yml"
    schema_file = tmp_path / "schema.yaml"
    yaml_file.write_text("name: CI\n", encoding="utf-8")
    schema_file.write_text("type: [\n", encoding="utf-8")

    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [yaml_file])

    result = _validator(schema_file).validate_against_schema(
        yml_path=yaml_file)

    assert result == 1


def test_validate_against_schema_returns_one_on_schema_read_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yaml_file = tmp_path / "workflow.yml"
    schema_file = tmp_path / "schema.json"
    yaml_file.write_text("name: CI\n", encoding="utf-8")
    _write_json_schema(schema_file)

    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [yaml_file])

    def raise_read_error(*args, **kwargs):
        raise OSError("cannot read schema")

    monkeypatch.setattr(Path, "read_text", raise_read_error, raising=False)

    result = _validator(schema_file).validate_against_schema(
        yml_path=yaml_file)

    assert result == 1


def test_validate_against_schema_returns_one_on_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yaml_file = tmp_path / "workflow.yml"
    schema_file = tmp_path / "schema.json"
    yaml_file.write_text("name: CI\n", encoding="utf-8")
    _write_json_schema(schema_file)

    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [yaml_file])
    monkeypatch.setattr(
        SchemaValidator,
        "_load_schema",
        lambda self, _: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = _validator(schema_file).validate_against_schema(
        yml_path=yaml_file)

    assert result == 1


def test_validate_against_schema_returns_one_when_no_yaml_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schema_file = tmp_path / "schema.json"
    _write_json_schema(schema_file)

    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [])

    result = _validator(schema_file).validate_against_schema(yml_path=tmp_path)

    assert result == 1


def test_validate_custom_pipeline_returns_zero_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "workflow.yml"
    schema_file = tmp_path / "schema.json"
    cfg_file.write_text("name: CI\n", encoding="utf-8")
    _write_json_schema(schema_file)
    schema_validator = _validator(schema_file)

    monkeypatch.setattr(
        SchemaValidator, "validate_against_schema", lambda self, **_: 0)
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [cfg_file])
    monkeypatch.setattr(
        vbs, "build_dot_scheme", lambda **_: cfg_file.with_suffix(".png")
    )

    result = schema_validator.validate_custom_pipeline(
        cfg_files=[cfg_file], yml2dot_exe=Path("yml2dot")
    )

    assert result == 0


def test_validate_custom_pipeline_returns_one_on_schema_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "workflow.yml"
    schema_file = tmp_path / "schema.json"
    cfg_file.write_text("name: CI\n", encoding="utf-8")
    _write_json_schema(schema_file)
    schema_validator = _validator(schema_file)

    monkeypatch.setattr(
        SchemaValidator, "validate_against_schema", lambda self, **_: 1)
    monkeypatch.setattr(
        vbs,
        "build_dot_scheme",
        lambda **_: pytest.fail("build_dot_scheme must not run when schema fails"),
    )

    result = schema_validator.validate_custom_pipeline(
        cfg_files=[cfg_file], yml2dot_exe=Path("yml2dot")
    )

    assert result == 1


def test_validate_custom_pipeline_returns_one_when_build_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file = tmp_path / "workflow.yml"
    schema_file = tmp_path / "schema.json"
    cfg_file.write_text("name: CI\n", encoding="utf-8")
    _write_json_schema(schema_file)
    schema_validator = _validator(schema_file)

    monkeypatch.setattr(
        SchemaValidator, "validate_against_schema", lambda self, **_: 0)
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [cfg_file])
    monkeypatch.setattr(vbs, "build_dot_scheme", lambda **_: None)

    result = schema_validator.validate_custom_pipeline(
        cfg_files=[cfg_file], yml2dot_exe=Path("yml2dot")
    )

    assert result == 1
