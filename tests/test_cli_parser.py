from pathlib import Path

import pytest

from src import cli_parser as cli


def test_compat_argument_parser_keeps_multiple_files_as_list() -> None:
    parser = cli._build_parser()

    args = parser.parse_args(["--files", "a.yml", "b.yml"])

    assert isinstance(args.files, list)
    assert args.files == [Path("a.yml"), Path("b.yml")]


def test_show_list_checks_prints_required_and_optional(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "EXTENDED_CHECKS", [".name", ".jobs"])
    monkeypatch.setattr(cli, "OPTIONAL_CHECKS", [".jobs[].needs"])

    rc = cli.show_list_checks()
    captured = capsys.readouterr()

    assert rc == 0
    assert "Required checks:" in captured.out
    assert "  .name" in captured.out
    assert "Optional checks" in captured.out
    assert "  .jobs[].needs" in captured.out


def test_show_description_prints_project_description(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "PROJECT_DESCRIPTION", "flowguard description")

    rc = cli.show_description()
    captured = capsys.readouterr()

    assert rc == 0
    assert "flowguard description" in captured.out


def test_show_version_prints_version_build_commit(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "__version__", "1.2.3")
    monkeypatch.setattr(cli, "__build__", "42")
    monkeypatch.setattr(cli, "__commit__", "abcdef0")

    rc = cli.show_version()
    captured = capsys.readouterr()

    assert rc == 0
    assert "flowguard 1.2.3 (build 42, commit abcdef0)" in captured.out
