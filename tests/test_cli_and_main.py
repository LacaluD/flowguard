from argparse import Namespace
from pathlib import Path

import pytest

import main as app_main
from src.cli_parser import _build_parser
from src.logger import MainLogger


class DummyParser:
    def __init__(self, namespace: Namespace) -> None:
        self._namespace = namespace

    def parse_args(self) -> Namespace:
        return self._namespace


def test_build_parser_parses_required_yml_files() -> None:
    parser = _build_parser()

    args = parser.parse_args(["--yml-files", "test.yml"])

    assert args.yml_files == Path("test.yml")
    assert args.exec_dir is None
    assert args.quiet is False


def test_build_parser_enables_quiet_flag() -> None:
    parser = _build_parser()

    args = parser.parse_args(["--yml-files", "test.yml", "--quiet"])

    assert args.quiet is True


def test_build_parser_rejects_missing_required_yml_files() -> None:
    parser = _build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_main_returns_error_when_executables_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    namespace = Namespace(
        yml_files=tmp_path / "any.yml", exec_dir=None, schema=None, quiet=False
    )
    monkeypatch.setattr(app_main, "_build_parser",
                        lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable", lambda _: None)

    result = app_main.main()

    assert result == 1


def test_main_success_flow_returns_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "workflow.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")
    png_file = yml_file.with_suffix(".png")

    namespace = Namespace(yml_files=yml_file,
                          exec_dir=None, schema=None, quiet=False)
    monkeypatch.setattr(app_main, "_build_parser",
                        lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable",
                        lambda _: Path("/bin/tool"))
    monkeypatch.setattr(app_main, "regular_validation", lambda **_: 0)

    result = app_main.main()

    assert result == 0


def test_main_uses_recursive_search_when_exec_dir_is_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "workflow.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    namespace = Namespace(
        yml_files=yml_file, exec_dir=tmp_path, schema=None, quiet=False
    )
    monkeypatch.setattr(app_main, "_build_parser",
                        lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable", lambda _: None)

    calls: list[tuple[str, Path]] = []

    def fake_recursive(fname: str, search_dir: Path) -> Path:
        calls.append((fname, search_dir))
        return tmp_path / fname

    monkeypatch.setattr(app_main, "find_executable_recursive", fake_recursive)
    monkeypatch.setattr(app_main, "regular_validation", lambda **_: 0)

    result = app_main.main()

    assert result == 0
    assert len(calls) == 2
    assert calls[0][1] == tmp_path


def test_main_returns_error_when_validation_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "workflow.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    namespace = Namespace(yml_files=yml_file,
                          exec_dir=None, schema=None, quiet=False)
    monkeypatch.setattr(app_main, "_build_parser",
                        lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable",
                        lambda _: Path("/bin/tool"))
    monkeypatch.setattr(app_main, "regular_validation", lambda **_: 1)

    result = app_main.main()

    assert result == 1


def test_main_success_output_goes_to_stdout(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "workflow.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")
    png_file = yml_file.with_suffix(".png")

    namespace = Namespace(yml_files=yml_file,
                          exec_dir=None, schema=None, quiet=False)
    monkeypatch.setattr(app_main, "_build_parser",
                        lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable",
                        lambda _: Path("/bin/tool"))
    monkeypatch.setattr(app_main, "regular_validation", lambda **_: 0)

    # Force handler reconfiguration so StreamHandlers bind to capsys streams.
    MainLogger._configured = False

    result = app_main.main()
    captured = capsys.readouterr()

    assert result == 0
    assert "Launching validation process without schema" in captured.out
    assert captured.err == ""


def test_main_error_output_goes_to_stderr_in_quiet_mode(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    namespace = Namespace(
        yml_files=tmp_path / "bad.yml", exec_dir=None, schema=None, quiet=True
    )
    monkeypatch.setattr(app_main, "_build_parser",
                        lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable", lambda _: None)

    # Force handler reconfiguration so StreamHandlers bind to capsys streams.
    MainLogger._configured = False

    result = app_main.main()
    captured = capsys.readouterr()

    assert result == 1
    assert "Not all required executables were found" in captured.err
    assert captured.out == ""
