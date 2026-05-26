import json
from pathlib import Path

from src.validation_by_schema import validate_against_schema


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


def test_validate_against_schema_valid_schema_and_yaml_returns_zero(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    yaml_file = tmp_path / "workflow.yml"

    _write_json_schema(schema_file)
    yaml_file.write_text("name: CI\njobs: {}\n", encoding="utf-8")

    result = validate_against_schema(
        yml_path=yaml_file, schema_file=schema_file)

    assert result == 0


def test_validate_against_schema_invalid_schema_returns_one(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    yaml_file = tmp_path / "workflow.yml"

    schema_file.write_text(
        '{"type": "object", "properties": "broken"}', encoding="utf-8")
    yaml_file.write_text("name: CI\n", encoding="utf-8")

    result = validate_against_schema(
        yml_path=yaml_file, schema_file=schema_file)

    assert result == 1


def test_validate_against_schema_invalid_yaml_returns_one(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    yaml_file = tmp_path / "workflow.yml"

    _write_json_schema(schema_file)
    yaml_file.write_text("name: [\n", encoding="utf-8")

    result = validate_against_schema(
        yml_path=yaml_file, schema_file=schema_file)

    assert result == 1


def test_validate_against_schema_directory_with_multiple_files_returns_one_on_any_invalid(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    yml_dir = tmp_path / "yamls"
    yml_dir.mkdir()

    valid_file = yml_dir / "good.yml"
    invalid_file = yml_dir / "bad.yaml"

    _write_json_schema(schema_file)
    valid_file.write_text("name: CI\n", encoding="utf-8")
    invalid_file.write_text("jobs: {}\n", encoding="utf-8")

    result = validate_against_schema(yml_path=yml_dir, schema_file=schema_file)

    assert result == 1


def test_validate_against_schema_empty_directory_returns_one(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    _write_json_schema(schema_file)

    result = validate_against_schema(
        yml_path=empty_dir, schema_file=schema_file)

    assert result == 1


def test_validate_against_schema_empty_yaml_file_returns_one(tmp_path: Path) -> None:
    schema_file = tmp_path / "schema.json"
    empty_yaml = tmp_path / "empty.yml"

    _write_json_schema(schema_file)
    empty_yaml.write_text("", encoding="utf-8")

    result = validate_against_schema(
        yml_path=empty_yaml, schema_file=schema_file)

    assert result == 1
