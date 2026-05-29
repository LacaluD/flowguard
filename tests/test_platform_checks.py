from pathlib import Path

import pytest

from src import platform_checks


def test_find_executable_prefers_path_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform_checks.shutil, "which",
                        lambda _: "/usr/bin/yq")

    result = platform_checks.find_executable("yq")

    assert result == Path("/usr/bin/yq")


def test_find_executable_finds_binary_in_extra_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    binary = tmp_path / "yq"
    binary.write_text("", encoding="utf-8")
    monkeypatch.setattr(platform_checks.shutil, "which", lambda _: None)

    def controlled_is_file(path_obj: Path) -> bool:
        return path_obj == binary

    def controlled_access(path_obj: Path, mode: int) -> bool:
        return path_obj == binary and mode == platform_checks.os.X_OK

    monkeypatch.setattr(Path, "is_file", controlled_is_file, raising=False)
    monkeypatch.setattr(platform_checks.os, "access", controlled_access)

    result = platform_checks.find_executable("yq", extra_paths=[tmp_path])

    assert result == binary


def test_find_executable_returns_none_when_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform_checks.shutil, "which", lambda _: None)
    monkeypatch.setattr(Path, "is_file", lambda _: False, raising=False)
    monkeypatch.setattr(platform_checks.os, "access", lambda *_: False)

    result = platform_checks.find_executable("missing_tool")

    assert result is None


def test_find_executable_windows_default_directory_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform_checks.shutil, "which", lambda _: None)
    monkeypatch.setattr(platform_checks.sys, "platform", "win32")

    target = Path("C:/") / "yq.exe"

    def fake_is_file(path_obj: Path) -> bool:
        return path_obj == target

    def fake_access(path_obj: Path, mode: int) -> bool:
        return path_obj == target and mode == platform_checks.os.X_OK

    monkeypatch.setattr(Path, "is_file", fake_is_file, raising=False)
    monkeypatch.setattr(platform_checks.os, "access", fake_access)

    result = platform_checks.find_executable("yq.exe")

    assert result == target


def test_find_executable_recursive_finds_nested_file(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    exe = nested / "yml2dot"
    exe.write_text("", encoding="utf-8")

    result = platform_checks.find_executable_recursive("yml2dot", tmp_path)

    assert result == exe


def test_find_executable_recursive_returns_none_for_missing_directory(
    tmp_path: Path,
) -> None:
    missing_dir = tmp_path / "does_not_exist"

    result = platform_checks.find_executable_recursive("yml2dot", missing_dir)

    assert result is None


def test_find_executable_recursive_returns_none_when_file_absent(
    tmp_path: Path,
) -> None:
    (tmp_path / "only_dirs").mkdir()

    result = platform_checks.find_executable_recursive("yml2dot", tmp_path)

    assert result is None
