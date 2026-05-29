from __future__ import annotations

from pathlib import Path

import pytest

from src import utils


class _FakePathObject:
    def __init__(self, *, is_file: bool, exists: bool, is_dir: bool) -> None:
        self._is_file = is_file
        self._exists = exists
        self._is_dir = is_dir

    def is_file(self) -> bool:
        return self._is_file

    def exists(self) -> bool:
        return self._exists

    def is_dir(self) -> bool:
        return self._is_dir

    def rglob(self, _pattern: str):
        return []


# _collect_yaml_files

def test_collect_yaml_files_success_respects_excluded_dirs(tmp_path: Path) -> None:
    keep = tmp_path / "cfg.yml"
    excluded_dir = tmp_path / "ignored"
    excluded_dir.mkdir()
    skipped = excluded_dir / "cfg.json"

    keep.write_text("name: ci\n", encoding="utf-8")
    skipped.write_text('{"name":"ci"}', encoding="utf-8")

    result = utils._collect_yaml_files(tmp_path, excluded_dirs=[excluded_dir])

    assert result == [keep]


def test_collect_yaml_files_failure_nonexistent_path_exits(mocker) -> None:
    fake_path = _FakePathObject(is_file=False, exists=False, is_dir=False)
    mocker.patch("src.utils.Path", return_value=fake_path)

    with pytest.raises(SystemExit):
        utils._collect_yaml_files(Path("missing"))


def test_collect_yaml_files_edge_existing_not_file_or_dir_exits(mocker) -> None:
    fake_path = _FakePathObject(is_file=False, exists=True, is_dir=False)
    mocker.patch("src.utils.Path", return_value=fake_path)

    with pytest.raises(SystemExit):
        utils._collect_yaml_files(Path("special"))


# _load_config_data

def test_load_config_data_success_yaml(tmp_path: Path) -> None:
    cfg = tmp_path / "wf.yml"
    cfg.write_text("name: CI\n", encoding="utf-8")

    result = utils._load_config_data(cfg)

    assert result == {"name": "CI"}


def test_load_config_data_success_toml(tmp_path: Path) -> None:
    cfg = tmp_path / "wf.toml"
    cfg.write_text('name = "CI"\n', encoding="utf-8")

    result = utils._load_config_data(cfg)

    assert result == {"name": "CI"}


def test_load_config_data_failure_unsupported_extension(tmp_path: Path) -> None:
    cfg = tmp_path / "wf.ini"
    cfg.write_text("name=CI\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported config format"):
        utils._load_config_data(cfg)
