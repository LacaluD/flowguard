import subprocess
from pathlib import Path

import pytest

from src import dot_schemas


def test_build_dot_scheme_returns_none_when_yml2dot_fails_with_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    def fake_run(cmd, *args, **kwargs):
        # First subprocess.run call is yml2dot in the current implementation.
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=2,
            stdout=b"",
            stderr=b"yml2dot parse failed",
        )

    monkeypatch.setattr(dot_schemas.subprocess, "run", fake_run)
    errors: list[str] = []
    monkeypatch.setattr(dot_schemas.logger, "error",
                        lambda message: errors.append(str(message)))

    result = dot_schemas.build_dot_scheme([yml_file], Path("yml2dot"))

    assert result is None
    assert any("yml2dot failed" in msg for msg in errors)
    assert any("yml2dot stderr: yml2dot parse failed" in msg for msg in errors)


def test_build_dot_scheme_does_not_call_dot_when_yml2dot_failed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append([str(part) for part in cmd])
        if len(calls) == 1:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout=b"",
                stderr=b"first stage failed",
            )
        pytest.fail("dot must not be executed when yml2dot fails")

    monkeypatch.setattr(dot_schemas.subprocess, "run", fake_run)

    result = dot_schemas.build_dot_scheme([yml_file], Path("yml2dot"))

    assert result is None
    assert len(calls) == 1


def test_build_dot_scheme_returns_none_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    def raise_timeout(cmd, *args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=2)

    monkeypatch.setattr(dot_schemas.subprocess, "run", raise_timeout)
    monkeypatch.setattr(dot_schemas, "count_timeout", lambda **_: 2)

    assert dot_schemas.build_dot_scheme([yml_file], Path("yml2dot")) is None


def test_build_dot_scheme_logs_dot_stderr_when_dot_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    yml_file = tmp_path / "wf.yml"
    yml_file.write_text("name: ci\n", encoding="utf-8")

    calls = {"n": 0}

    def fake_run(cmd, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=b"digraph G {}",
                stderr=b"",
            )
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="dot failed as text",
        )

    monkeypatch.setattr(dot_schemas.subprocess, "run", fake_run)
    errors: list[str] = []
    monkeypatch.setattr(dot_schemas.logger, "error",
                        lambda message: errors.append(str(message)))

    result = dot_schemas.build_dot_scheme([yml_file], Path("yml2dot"))

    assert result is None
    assert any("dot stderr: dot failed as text" in msg for msg in errors)
