from argparse import Namespace
from pathlib import Path

import pytest

import main as app_main


class DummyParser:
    def __init__(self, namespace: Namespace) -> None:
        self._namespace = namespace

    def parse_args(self) -> Namespace:
        return self._namespace


def test_main_schema_branch_calls_validate_custom_pipeline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    namespace = Namespace(
        files=tmp_path / "wf.yml",
        exec_dir=None,
        schema=tmp_path / "schema.json",
        quiet=False,
        list_checks=False,
        description=False,
        version=False,
        difference=False,
        no_optional_checks=False,
        output_format="svg",
    )
    monkeypatch.setattr(app_main, "_build_parser",
                        lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable",
                        lambda _: Path("/bin/tool"))

    called: dict[str, object] = {}

    def fake_validate(*, cfg_files: Path, val_schema: Path, yml2dot_exe: Path) -> int:
        called["cfg_files"] = cfg_files
        called["val_schema"] = val_schema
        called["yml2dot_exe"] = yml2dot_exe
        return 0

    monkeypatch.setattr(app_main, "validate_custom_pipeline", fake_validate)
    monkeypatch.setattr(
        app_main,
        "regular_validation",
        lambda **_: pytest.fail("regular_validation must not run in schema mode"),
    )

    assert app_main.main() == 0
    assert called["cfg_files"] == namespace.files
    assert called["val_schema"] == namespace.schema
    assert called["yml2dot_exe"] == Path("/bin/tool")
