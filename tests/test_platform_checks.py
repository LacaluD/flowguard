from pathlib import Path

import pytest

from src import platform_checks


def test_find_executable_prefers_path_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_checks.shutil, "which",
                        lambda _: "/usr/bin/yq")

    result = platform_checks.find_executable("yq")

    assert result == Path("/usr/bin/yq")


def test_find_executable_finds_binary_in_extra_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    binary = tmp_path / "yq"
    binary.write_text("", encoding="utf-8")
    monkeypatch.setattr(platform_checks.shutil, "which", lambda _: None)

    def controlled_exists(path_obj: Path) -> bool:
        return path_obj == binary

    monkeypatch.setattr(Path, "exists", controlled_exists, raising=False)

    result = platform_checks.find_executable("yq", extra_paths=[tmp_path])

    assert result == binary


def test_find_executable_returns_none_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_checks.shutil, "which", lambda _: None)
    monkeypatch.setattr(Path, "exists", lambda _: False, raising=False)

    result = platform_checks.find_executable("missing_tool")

    assert result is None


def test_find_executable_recursive_finds_nested_file(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    exe = nested / "yml2dot"
    exe.write_text("", encoding="utf-8")

    result = platform_checks.find_executable_recursive("yml2dot", tmp_path)

    assert result == exe


def test_find_executable_recursive_returns_none_for_missing_directory(tmp_path: Path) -> None:
    missing_dir = tmp_path / "does_not_exist"

    result = platform_checks.find_executable_recursive("yml2dot", missing_dir)

    assert result is None


def test_find_executable_recursive_returns_none_when_file_absent(tmp_path: Path) -> None:
    (tmp_path / "only_dirs").mkdir()

    result = platform_checks.find_executable_recursive("yml2dot", tmp_path)

    assert result is None
