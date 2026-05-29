from pathlib import Path

import pytest

from src import utils


def _write_file_with_size(path: Path, size_mb: float) -> None:
    size_bytes = int(size_mb * 1024 * 1024)
    with path.open("wb") as fh:
        fh.truncate(size_bytes)


def test_check_for_empty_file_whitespace_only_returns_one(tmp_path: Path) -> None:
    f = tmp_path / "blank.yml"
    f.write_text("   \n\t\n", encoding="utf-8")

    assert utils.check_for_empty_file(f) == 1


def test_count_timeout_returns_none_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yml"
    assert utils.count_timeout(missing, "yq") is None


def test_count_timeout_for_yml2dot_ranges(tmp_path: Path) -> None:
    small = tmp_path / "small.yml"
    medium = tmp_path / "medium.yml"
    large = tmp_path / "large.yml"

    _write_file_with_size(small, 0.4)
    _write_file_with_size(medium, 1.5)
    _write_file_with_size(large, 3.5)

    assert utils.count_timeout(small, "yml2dot") == 25
    assert utils.count_timeout(medium, "yml2dot") == 40
    assert utils.count_timeout(large, "yml2dot") == 80


def test_count_timeout_for_yq_ranges(tmp_path: Path) -> None:
    small = tmp_path / "small.yml"
    large = tmp_path / "large.yml"

    _write_file_with_size(small, 1.0)
    _write_file_with_size(large, 5.0)

    assert utils.count_timeout(small, "yq") == 20
    assert utils.count_timeout(large, "yq") == 40


def test_count_timeout_unknown_tool_returns_none(tmp_path: Path) -> None:
    f = tmp_path / "x.yml"
    f.write_text("name: ci\n", encoding="utf-8")
    assert utils.count_timeout(f, "unknown") is None


def test_extract_job_view_success_returns_selected_job_and_name() -> None:
    data = {
        "name": "CI",
        "jobs": {"build": {"runs-on": "ubuntu-latest"}},
    }

    result = utils._extract_job_view(data, job_name="build", file_path=Path("wf.yml"))

    assert result == {
        "jobs": {"build": {"runs-on": "ubuntu-latest"}},
        "name": "CI",
    }


def test_extract_job_view_raises_for_non_mapping_root() -> None:
    with pytest.raises(ValueError, match="expected mapping root"):
        utils._extract_job_view([1, 2, 3], job_name="build", file_path=Path("wf.yml"))


def test_extract_job_view_raises_when_jobs_mapping_missing() -> None:
    with pytest.raises(ValueError, match="top-level 'jobs' mapping is missing"):
        utils._extract_job_view(
            {"name": "CI"}, job_name="build", file_path=Path("wf.yml")
        )
