from pathlib import Path

import pytest

from src import utils


def test_check_for_empty_file_whitespace_only_returns_one(tmp_path: Path) -> None:
    f = tmp_path / "blank.yml"
    f.write_text("   \n\t\n", encoding="utf-8")

    assert utils.check_for_empty_file(f) == 1


def test_count_timeout_returns_none_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yml"
    assert utils.count_timeout(missing, "yq") is None


def test_count_timeout_for_yml2dot_ranges(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    f = tmp_path / "x.yml"
    f.write_text("name: ci\n", encoding="utf-8")

    class FakeStat:
        def __init__(self, size_mb: float) -> None:
            self.st_size = int(size_mb * 1024 * 1024)

    monkeypatch.setattr(
        Path, "stat", lambda self: FakeStat(0.4), raising=False)
    assert utils.count_timeout(f, "yml2dot") == 25

    monkeypatch.setattr(
        Path, "stat", lambda self: FakeStat(1.5), raising=False)
    assert utils.count_timeout(f, "yml2dot") == 40

    monkeypatch.setattr(
        Path, "stat", lambda self: FakeStat(3.5), raising=False)
    assert utils.count_timeout(f, "yml2dot") == 80


def test_count_timeout_for_yq_ranges(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    f = tmp_path / "x.yml"
    f.write_text("name: ci\n", encoding="utf-8")

    class FakeStat:
        def __init__(self, size_mb: float) -> None:
            self.st_size = int(size_mb * 1024 * 1024)

    monkeypatch.setattr(
        Path, "stat", lambda self: FakeStat(1.0), raising=False)
    assert utils.count_timeout(f, "yq") == 20

    monkeypatch.setattr(
        Path, "stat", lambda self: FakeStat(5.0), raising=False)
    assert utils.count_timeout(f, "yq") == 40


def test_count_timeout_unknown_tool_returns_none(tmp_path: Path) -> None:
    f = tmp_path / "x.yml"
    f.write_text("name: ci\n", encoding="utf-8")
    assert utils.count_timeout(f, "unknown") is None
