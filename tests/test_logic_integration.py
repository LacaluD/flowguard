import subprocess
from pathlib import Path

from src import main_validation_logic


def test_validate_config_integration_success_with_mocked_yq(
    monkeypatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "workflow.yml"
    yml_file.write_text(
        "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps: []\n",
        encoding="utf-8",
    )

    def fake_run(cmd, check, stdout, stderr, text, timeout):
        expression = cmd[2]
        outputs = {
            ".": "ok\n",
            ".name": "CI\n",
            ".jobs": "build\n",
            ".on": "push\n",
            ".jobs.*.steps": "[]\n",
            ".jobs.*.runs-on": "ubuntu-latest\n",
        }
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=outputs[expression], stderr=""
        )

    monkeypatch.setattr(main_validation_logic.subprocess, "run", fake_run)

    result = main_validation_logic.validate_config(tmp_path, Path("yq"))

    assert result == 0


def test_validate_config_integration_fails_on_yq_parse_error(
    monkeypatch, tmp_path: Path
) -> None:
    yml_file = tmp_path / "broken.yml"
    yml_file.write_text("name: [\n", encoding="utf-8")

    def fake_run(cmd, check, stdout, stderr, text, timeout):
        raise subprocess.CalledProcessError(
            returncode=1, cmd=cmd, stderr="yaml parse error"
        )

    monkeypatch.setattr(main_validation_logic.subprocess, "run", fake_run)

    result = main_validation_logic.validate_config(tmp_path, Path("yq"))

    assert result == 1
