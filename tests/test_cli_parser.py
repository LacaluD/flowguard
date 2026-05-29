from pathlib import Path

import pytest

from src import cli_parser as cli


def test_compat_argument_parser_keeps_multiple_files_as_list() -> None:
    parser = cli._build_parser()

    args = parser.parse_args(["--files", "a.yml", "b.yml"])

    assert isinstance(args.files, list)
    assert args.files == [Path("a.yml"), Path("b.yml")]


def test_compat_argument_parser_unwraps_single_file_to_path() -> None:
    parser = cli._build_parser()

    args = parser.parse_args(["--files", "single.yml"])

    assert isinstance(args.files, Path)
    assert args.files == Path("single.yml")


def test_build_parser_success_flags_and_paths() -> None:
    parser = cli._build_parser()

    args = parser.parse_args(
        [
            "--exec-dir",
            "bin",
            "--schema",
            "schema.json",
            "--files",
            "cfg.yml",
            "--difference",
            "--job",
            "build",
            "--output-format",
            "png",
            "--quiet",
            "--no-optional-checks",
            "--list-checks",
            "--description",
            "--version",
        ]
    )

    assert args.exec_dir == Path("bin")
    assert args.schema == Path("schema.json")
    assert args.files == Path("cfg.yml")
    assert args.difference is True
    assert args.job == "build"
    assert args.output_format == "png"
    assert args.quiet is True
    assert args.no_optional_checks is True
    assert args.list_checks is True
    assert args.description is True
    assert args.version is True


def test_build_parser_edge_defaults_without_args() -> None:
    parser = cli._build_parser()

    args = parser.parse_args([])

    assert args.exec_dir is None
    assert args.files is None
    assert args.schema is None
    assert args.difference is False
    assert args.job is None
    assert args.output_format == "svg"
    assert args.quiet is False
    assert args.no_optional_checks is False
    assert args.list_checks is False
    assert args.description is False
    assert args.version is False


def test_build_parser_edge_short_aliases() -> None:
    parser = cli._build_parser()

    args = parser.parse_args(
        ["-f", "a.yml", "b.yml", "-diff", "-o", "dot", "-q"])

    assert args.files == [Path("a.yml"), Path("b.yml")]
    assert args.difference is True
    assert args.output_format == "dot"
    assert args.quiet is True


def test_build_parser_fail_invalid_output_format_raises_system_exit() -> None:
    parser = cli._build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--output-format", "jpeg"])


def test_build_parser_fail_missing_files_value_raises_system_exit() -> None:
    parser = cli._build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--files"])


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


def test_show_list_checks_edge_empty_lists(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "EXTENDED_CHECKS", [])
    monkeypatch.setattr(cli, "OPTIONAL_CHECKS", [])

    rc = cli.show_list_checks()
    captured = capsys.readouterr()

    assert rc == 0
    assert "Required checks:" in captured.out
    assert "Optional checks" in captured.out


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
