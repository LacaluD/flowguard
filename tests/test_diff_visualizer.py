from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve(
).parents[1] / "src" / "diff_visualizer.py"
_SPEC = importlib.util.spec_from_file_location("diff_visualizer", MODULE_PATH)
assert _SPEC and _SPEC.loader

# Keep tests runnable on Python < 3.11 by providing a small tomli stub.
if "tomli" not in sys.modules:
    tomli_stub = types.ModuleType("tomli")

    def _default_tomli_load(_fh: io.BufferedReader) -> dict[str, object]:
        return {}

    tomli_stub.load = _default_tomli_load  # type: ignore[attr-defined]
    sys.modules["tomli"] = tomli_stub

mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def test_flatten_handles_nested_mappings_and_lists() -> None:
    data = {
        "service": {
            "name": "api",
            "ports": [80, 443],
            "meta": {"enabled": True},
        }
    }

    result = mod._flatten(data)

    assert result == {
        "service.name": "api",
        "service.ports.0": "80",
        "service.ports.1": "443",
        "service.meta.enabled": "True",
    }


def test_flatten_returns_empty_for_empty_mapping_and_list() -> None:
    assert mod._flatten({}) == {}
    assert mod._flatten([]) == {}


def test_flatten_list_with_nested_mapping_item() -> None:
    data = [{"a": {"b": 1}}]

    result = mod._flatten(data)

    assert result == {"0.a.b": "1"}


def test_get_diff_returns_added_removed_changed_sets() -> None:
    first_flat = {"a": "1", "b": "2", "same": "x"}
    second_flat = {"a": "1", "c": "3", "same": "y"}

    added, removed, changed = mod._get_diff(first_flat, second_flat)

    assert added == {"c"}
    assert removed == {"b"}
    assert changed == {"same"}


def test_get_diff_empty_inputs() -> None:
    added, removed, changed = mod._get_diff({}, {})
    assert added == set()
    assert removed == set()
    assert changed == set()


def test_parse_yml_returns_empty_dict_for_empty_file(tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.yml"
    empty_file.write_text("", encoding="utf-8")

    parsed = mod._parse_yml(empty_file)

    assert parsed == {}


def test_parse_yml_valid_file(tmp_path: Path) -> None:
    file_path = tmp_path / "x.yml"
    file_path.write_text("a:\n  b: 2\n", encoding="utf-8")

    parsed = mod._parse_yml(file_path)

    assert parsed == {"a": {"b": 2}}


def test_parse_json_success(tmp_path: Path) -> None:
    json_file = tmp_path / "data.json"
    json_file.write_text('{"a": 1, "b": [1, 2]}', encoding="utf-8")

    parsed = mod._parse_json(json_file)

    assert parsed == {"a": 1, "b": [1, 2]}


def test_parse_json_failure_invalid_json(tmp_path: Path) -> None:
    json_file = tmp_path / "broken.json"
    json_file.write_text('{"a": 1,', encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        mod._parse_json(json_file)


def test_parse_toml_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    toml_file = tmp_path / "cfg.toml"
    toml_file.write_text('name = "app"\n', encoding="utf-8")

    def fake_load(file_obj: io.BufferedReader) -> dict[str, object]:
        assert file_obj.read().decode("utf-8") == 'name = "app"\n'
        file_obj.seek(0)
        return {"name": "app"}

    monkeypatch.setattr(mod.tomllib, "load", fake_load)

    parsed = mod._parse_toml(toml_file)

    assert parsed == {"name": "app"}


def test_parse_toml_failure_propagates_loader_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    toml_file = tmp_path / "broken.toml"
    toml_file.write_text("name = \"app\"\n", encoding="utf-8")

    def fake_load(_file_obj: io.BufferedReader) -> dict[str, object]:
        raise ValueError("invalid toml")

    monkeypatch.setattr(mod.tomllib, "load", fake_load)

    with pytest.raises(ValueError, match="invalid toml"):
        mod._parse_toml(toml_file)


def test_parse_file_yaml_success(tmp_path: Path) -> None:
    file_path = tmp_path / "cfg.yaml"
    file_path.write_text("name: app\n", encoding="utf-8")

    parsed = mod._parse_file(file_path)

    assert parsed == {"name": "app"}


def test_parse_file_json_success(tmp_path: Path) -> None:
    file_path = tmp_path / "cfg.json"
    file_path.write_text('{"name": "app"}', encoding="utf-8")

    parsed = mod._parse_file(file_path)

    assert parsed == {"name": "app"}


def test_parse_file_toml_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "cfg.toml"
    file_path.write_text('name = "app"\n', encoding="utf-8")
    monkeypatch.setattr(mod, "_parse_toml", lambda _path: {"name": "app"})

    parsed = mod._parse_file(file_path)

    assert parsed == {"name": "app"}


def test_parse_file_uppercase_toml_extension_edge_case(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "cfg.TOML"
    file_path.write_text('x = 1\n', encoding="utf-8")
    monkeypatch.setattr(mod, "_parse_toml", lambda _path: {"x": 1})

    parsed = mod._parse_file(file_path)

    assert parsed == {"x": 1}


def test_parse_file_failure_unsupported_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "cfg.ini"
    file_path.write_text("k = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        mod._parse_file(file_path)


def test_get_cfg_difference_dot_writes_dot_file_without_graphviz(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_file = tmp_path / "old.yml"
    new_file = tmp_path / "new.yml"
    old_file.write_text("a: 1\n", encoding="utf-8")
    new_file.write_text("a: 2\n", encoding="utf-8")

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "subprocess.run should not be called for dot output")

    monkeypatch.setattr(mod.subprocess, "run", fail_if_called)

    rc = mod.get_cfg_difference(
        old_file, new_file, dot_exec=Path("dot"), output_format="dot")

    assert rc == 0
    assert new_file.with_suffix(".diff.dot").exists()


def test_get_cfg_difference_svg_success_calls_graphviz_and_cleans_dot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_file = tmp_path / "old.yml"
    new_file = tmp_path / "new.yml"
    old_file.write_text("root:\n  a: 1\n", encoding="utf-8")
    new_file.write_text("root:\n  a: 2\n", encoding="utf-8")

    def fake_run(args: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        assert args[0] == Path("dot")
        assert args[1] == "-Tsvg"
        out_index = args.index("-o") + 1
        Path(args[out_index]).write_text("<svg/>", encoding="utf-8")
        assert capture_output is True
        assert text is True
        assert check is False
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    rc = mod.get_cfg_difference(
        old_file, new_file, dot_exec=Path("dot"), output_format="svg")

    assert rc == 0
    assert new_file.with_suffix(".diff.svg").exists()
    assert not new_file.with_suffix(".diff.dot").exists()


def test_get_cfg_difference_png_failure_returns_one_and_cleans_dot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_file = tmp_path / "old.yml"
    new_file = tmp_path / "new.yml"
    old_file.write_text("a: 1\n", encoding="utf-8")
    new_file.write_text("a: 2\n", encoding="utf-8")

    def fake_run(args: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        assert args[1] == "-Tpng"
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    rc = mod.get_cfg_difference(
        old_file, new_file, dot_exec=Path("dot"), output_format="png")

    assert rc == 1
    assert not new_file.with_suffix(".diff.dot").exists()


def test_get_cfg_difference_with_toml_inputs_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_file = tmp_path / "old.toml"
    new_file = tmp_path / "new.toml"
    old_file.write_text('a = 1\n', encoding="utf-8")
    new_file.write_text('a = 2\n', encoding="utf-8")

    monkeypatch.setattr(mod, "_parse_file", lambda path: {
                        "a": 1} if path == old_file else {"a": 2})

    def fake_run(args: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        assert args[1] == "-Tsvg"
        Path(args[args.index("-o") + 1]).write_text("<svg/>", encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    rc = mod.get_cfg_difference(old_file, new_file, dot_exec=Path("dot"))

    assert rc == 0
    assert new_file.with_suffix(".diff.svg").exists()


def test_visualize_cfgs_returns_zero_without_difference_flag() -> None:
    rc = mod.visualize_cfgs(
        [Path("a.yml"), Path("b.yml")],
        dot_exec=Path("dot"),
        difference=False,
    )

    assert rc == 0


def test_visualize_cfgs_fails_when_file_count_not_equal_two() -> None:
    rc_one = mod.visualize_cfgs(
        [Path("a.yml")], dot_exec=Path("dot"), difference=True)
    rc_three = mod.visualize_cfgs(
        [Path("a.yml"), Path("b.yml"), Path("c.yml")],
        dot_exec=Path("dot"),
        difference=True,
    )

    assert rc_one == 1
    assert rc_three == 1


def test_visualize_cfgs_fails_for_invalid_extension() -> None:
    rc = mod.visualize_cfgs(
        [Path("a.yml"), Path("b.txt")],
        dot_exec=Path("dot"),
        difference=True,
    )

    assert rc == 1


def test_visualize_cfgs_accepts_toml_and_mixed_case_extensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_get_cfg_difference(
        fst_file: Path,
        sec_file: Path,
        dot_exec: Path,
        output_format: str = "svg",
    ) -> int:
        captured["fst"] = fst_file
        captured["sec"] = sec_file
        captured["dot_exec"] = dot_exec
        captured["fmt"] = output_format
        return 0

    monkeypatch.setattr(mod, "get_cfg_difference", fake_get_cfg_difference)

    rc = mod.visualize_cfgs(
        [Path("old.TOML"), Path("new.yaml")],
        dot_exec=Path("dot"),
        difference=True,
        output_format="png",
    )

    assert rc == 0
    assert captured == {
        "fst": Path("old.TOML"),
        "sec": Path("new.yaml"),
        "dot_exec": Path("dot"),
        "fmt": "png",
    }


def test_build_dot_covers_added_and_removed_classification() -> None:
    dot_text = mod._build_dot(
        data={"k": 1},
        fst_flat={"k": "0", "old": "x", "parent.child": "y"},
        added={"k"},
        removed={"old", "parent.child"},
        changed=set(),
    )

    assert '#ccffcc' in dot_text
    assert '#ffcccc' in dot_text
    assert 'old' in dot_text
    assert 'child' in dot_text


def test_build_dot_classifies_removed_key_present_in_data() -> None:
    dot_text = mod._build_dot(
        data={"legacy": 1},
        fst_flat={"legacy": "1"},
        added=set(),
        removed={"legacy"},
        changed=set(),
    )

    assert '#ffcccc' in dot_text


def test_build_dot_handles_list_value_branch() -> None:
    dot_text = mod._build_dot(
        data={"root": [1, 2]},
        fst_flat={},
        added=set(),
        removed=set(),
        changed=set(),
    )

    assert 'label="root"' in dot_text
    assert 'label="0"' in dot_text
    assert 'label="1"' in dot_text


def test_build_dot_handles_top_level_list_data() -> None:
    dot_text = mod._build_dot(
        data=[{"a": 1}],
        fst_flat={},
        added=set(),
        removed=set(),
        changed=set(),
    )

    assert 'label="0"' in dot_text
    assert 'label="a"' in dot_text


def test_build_dot_handles_top_level_scalar_data() -> None:
    dot_text = mod._build_dot(
        data="scalar",
        fst_flat={},
        added=set(),
        removed=set(),
        changed=set(),
    )

    assert 'label="root"' in dot_text
