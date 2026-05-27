from argparse import Namespace
from pathlib import Path

import pytest

import main as app_main


class DummyParser:
    def __init__(self, namespace: Namespace) -> None:
        self._namespace = namespace

    def parse_args(self) -> Namespace:
        return self._namespace


def test_main_schema_branch_calls_validate_against_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    namespace = Namespace(
        yml_files=tmp_path / "wf.yml",
        exec_dir=None,
        schema=tmp_path / "schema.json",
        quiet=False,
    )
    monkeypatch.setattr(app_main, "_build_parser", lambda: DummyParser(namespace))
    monkeypatch.setattr(app_main, "find_executable", lambda _: Path("/bin/tool"))

    called: dict[str, object] = {}

    def fake_validate(*, yml_path: Path, schema_file: Path) -> int:
        called["yml_path"] = yml_path
        called["schema_file"] = schema_file
        return 0

    monkeypatch.setattr(app_main, "validate_against_schema", fake_validate)
    monkeypatch.setattr(
        app_main,
        "regular_validation",
        lambda **_: pytest.fail("regular_validation must not run in schema mode"),
    )

    assert app_main.main() == 0
    assert called["yml_path"] == namespace.yml_files
    assert called["schema_file"] == namespace.schema
