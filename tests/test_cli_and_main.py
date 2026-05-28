from argparse import Namespace
import runpy
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


def test_build_parser_parses_required_cfg_files() -> None:
    parser = _build_parser()

    args = parser.parse_args(["--files", "test.yml"])

    assert args.files == Path("test.yml")
    assert args.exec_dir is None
    assert args.quiet is False


def test_build_parser_enables_quiet_flag() -> None:
    parser = _build_parser()

    args = parser.parse_args(["--files", "test.yml", "--quiet"])

    assert args.quiet is True


def test_build_parser_rejects_missing_required_cfg_files() -> None:
    parser = _build_parser()
    args = parser.parse_args([])

    assert args.files is None


def test_main_returns_error_when_executables_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    namespace = Namespace(
        files=tmp_path / "any.yml",
        exec_dir=None,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=False,
        description=False,
        version=False,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable", lambda _: None)

    result = app_main.main()

    assert result == 1


def test_main_success_flow_returns_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "workflow.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")
    png_file = yml_file.with_suffix(".png")

    namespace = Namespace(
        files=yml_file,
        exec_dir=None,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=False,
        description=False,
        version=False,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable", lambda _: Path("/bin/tool"))
    monkeypatch.setattr(app_main, "regular_validation", lambda **_: 0)

    result = app_main.main()

    assert result == 0


def test_main_uses_recursive_search_when_exec_dir_is_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "workflow.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    namespace = Namespace(
        files=yml_file,
        exec_dir=tmp_path,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=False,
        description=False,
        version=False,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
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

    namespace = Namespace(
        files=yml_file,
        exec_dir=None,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=False,
        description=False,
        version=False,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable", lambda _: Path("/bin/tool"))
    monkeypatch.setattr(app_main, "regular_validation", lambda **_: 1)

    result = app_main.main()

    assert result == 1


def test_main_success_output_goes_to_stdout(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "workflow.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")
    png_file = yml_file.with_suffix(".png")

    namespace = Namespace(
        files=yml_file,
        exec_dir=None,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=False,
        description=False,
        version=False,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable", lambda _: Path("/bin/tool"))
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
        files=tmp_path / "bad.yml",
        exec_dir=None,
        exclude_dir=None,
        schema=None,
        quiet=True,
        list_checks=False,
        description=False,
        version=False,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable", lambda _: None)

    # Force handler reconfiguration so StreamHandlers bind to capsys streams.
    MainLogger._configured = False

    result = app_main.main()
    captured = capsys.readouterr()

    assert result == 1
    assert "Not all required executables were found" in captured.err
    assert captured.out == ""


def test_main_returns_show_list_checks_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    namespace = Namespace(
        files=tmp_path / "wf.yml",
        exec_dir=None,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=True,
        description=False,
        version=False,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "show_list_checks", lambda: 7)

    assert app_main.main() == 7


def test_main_returns_show_description_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    namespace = Namespace(
        files=tmp_path / "wf.yml",
        exec_dir=None,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=False,
        description=True,
        version=False,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "show_description", lambda: 8)

    assert app_main.main() == 8


def test_main_returns_show_version_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    namespace = Namespace(
        files=tmp_path / "wf.yml",
        exec_dir=None,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=False,
        description=False,
        version=True,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "show_version", lambda: 9)

    assert app_main.main() == 9


def test_main_difference_mode_uses_recursive_dot_and_calls_visualizer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_a = tmp_path / "a.yml"
    cfg_b = tmp_path / "b.yml"
    cfg_a.write_text("a: 1\n", encoding="utf-8")
    cfg_b.write_text("a: 2\n", encoding="utf-8")

    namespace = Namespace(
        files=cfg_a,
        exec_dir=tmp_path,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=False,
        description=False,
        version=False,
        difference=True,
        no_optional_checks=False,
        output_format="png",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))

    def fake_find_executable(name: str):
        if name == "dot":
            return None
        return Path("/bin/tool")

    monkeypatch.setattr(app_main, "find_executable", fake_find_executable)

    recursive_calls: list[tuple[str, Path]] = []

    def fake_recursive(fname: str, search_dir: Path) -> Path:
        recursive_calls.append((fname, search_dir))
        return tmp_path / fname

    monkeypatch.setattr(app_main, "find_executable_recursive", fake_recursive)

    captured: dict[str, object] = {}

    def fake_visualize(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(app_main, "visualize_cfgs", fake_visualize)

    assert app_main.main() == 0
    assert recursive_calls[-1][0] in {"dot", "dot.exe"}
    assert captured["files"] == [cfg_a]
    assert captured["difference"] is True
    assert captured["output_format"] == "png"


def test_main_difference_mode_logs_missing_dot_when_not_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_a = tmp_path / "a.yml"
    cfg_a.write_text("a: 1\n", encoding="utf-8")

    namespace = Namespace(
        files=cfg_a,
        exec_dir=None,
        exclude_dir=None,
        schema=None,
        quiet=False,
        list_checks=False,
        description=False,
        version=False,
        difference=True,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))

    def fake_find_executable(name: str):
        if name == "dot":
            return None
        return Path("/bin/tool")

    monkeypatch.setattr(app_main, "find_executable", fake_find_executable)

    messages: list[str] = []

    class FakeLogger:
        def info(self, msg: str) -> None:
            messages.append(f"I:{msg}")

        def error(self, msg: str) -> None:
            messages.append(f"E:{msg}")

    monkeypatch.setattr(
        app_main,
        "MainLogger",
        lambda: type(
            "L", (), {"init_logger": lambda self, quiet=False: FakeLogger()}
        )(),
    )

    assert app_main.main() == 1
    assert any(line.startswith("E:dot:") for line in messages)


def test_main_module_runs_as_script(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["main.py", "--version"])

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("main", run_name="__main__")

    assert exc.value.code == 0
