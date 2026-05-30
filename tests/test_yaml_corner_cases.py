import json
from pathlib import Path

from src import validation_by_schema as vbs
from src.validation_by_schema import SchemaValidator


def _write_permissive_schema(schema_path: Path) -> None:
    """Write a schema that validates any YAML mapping object."""
    schema = {"type": "object"}
    schema_path.write_text(json.dumps(schema), encoding="utf-8")


def _validate_file_with_permissive_schema(
    monkeypatch, tmp_path: Path, yaml_file: Path
) -> int:
    schema_file = tmp_path / "schema.json"
    _write_permissive_schema(schema_file)
    monkeypatch.setattr(vbs, "_collect_yaml_files", lambda *_: [yaml_file])
    return SchemaValidator(schema_file).validate_against_schema(yml_path=yaml_file)


def test_unicode_yaml_is_valid(monkeypatch, tmp_path: Path) -> None:
    yaml_file = tmp_path / "unicode.yml"
    yaml_file.write_text(
        'name: "\u041f\u0440\u0438\u0432\u0435\u0442"\nversion: "\u65e5\u672c\u8a9e"\n',
        encoding="utf-8",
    )

    assert _validate_file_with_permissive_schema(monkeypatch, tmp_path, yaml_file) == 0


def test_bom_yaml_is_valid(monkeypatch, tmp_path: Path) -> None:
    yaml_file = tmp_path / "bom.yml"
    yaml_file.write_bytes(b"\xef\xbb\xbfname: test\nversion: 1.0\n")

    assert _validate_file_with_permissive_schema(monkeypatch, tmp_path, yaml_file) == 0


def test_crlf_yaml_is_valid(monkeypatch, tmp_path: Path) -> None:
    yaml_file = tmp_path / "crlf.yml"
    yaml_file.write_bytes(b"name: test\r\nversion: 1.0\r\n")

    assert _validate_file_with_permissive_schema(monkeypatch, tmp_path, yaml_file) == 0


def test_tabs_indentation_yaml_is_invalid(monkeypatch, tmp_path: Path) -> None:
    yaml_file = tmp_path / "tabs.yml"
    yaml_file.write_text("name: test\n\tversion: 1.0\n", encoding="utf-8")

    assert _validate_file_with_permissive_schema(monkeypatch, tmp_path, yaml_file) == 1


def test_mixed_indentation_yaml_is_invalid(monkeypatch, tmp_path: Path) -> None:
    yaml_file = tmp_path / "mixed.yml"
    yaml_file.write_text("root:\n  child1: a\n   child2: b\n", encoding="utf-8")

    assert _validate_file_with_permissive_schema(monkeypatch, tmp_path, yaml_file) == 1


def test_empty_values_yaml_is_valid(monkeypatch, tmp_path: Path) -> None:
    yaml_file = tmp_path / "empty_vals.yml"
    yaml_file.write_text("name:\nversion:\ndescription: null\n", encoding="utf-8")

    assert _validate_file_with_permissive_schema(monkeypatch, tmp_path, yaml_file) == 0


def test_deeply_nested_yaml_is_valid(monkeypatch, tmp_path: Path) -> None:
    yaml_file = tmp_path / "deep.yml"

    lines: list[str] = []
    for depth in range(50):
        lines.append("  " * depth + f"level{depth}:")
    yaml_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert _validate_file_with_permissive_schema(monkeypatch, tmp_path, yaml_file) == 0
