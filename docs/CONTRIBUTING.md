# Contributing to flowguard

Thank you for contributing to flowguard.

## Prerequisites

- Python 3.10+
- Optional but recommended for local CLI features: `yq`, `yml2dot`, and `dot` (Graphviz)

## Local setup

```bash
git clone https://github.com/LacaluD/flowguard.git
cd flowguard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install ".[dev]"
```

## Run checks before opening PR

### Tests

```bash
python -m pytest -q -c configs/pytest.ini
```

### Coverage

```bash
python -m coverage run -m pytest -q -c configs/pytest.ini
python -m coverage report --fail-under=90
```

### Lint and type checks

```bash
python -m mypy -p src --config-file configs/mypy.ini
python -m bandit -c configs/bandit.yml -r main.py src
```

## Branch and commit workflow

1. Create a topic branch from `main`.
2. Keep changes focused and small.
3. Add or update tests for behavioral changes.
4. Update docs when CLI behavior or examples change.
5. Open a PR with a clear summary and testing notes.

## Documentation expectations

- Keep examples runnable against current repository files.
- Keep CLI options in docs aligned with `src/cli_parser.py`.
- Prefer concise, operational wording.

## Release checklist

1. Run the full test suite and verify all tests pass.
2. Run coverage and confirm the threshold (`>= 90%`) is met.
3. Run type and security checks (`mypy`, `bandit`) with no new issues.
4. Verify CLI examples from `README.md` still work with current flags.
5. Confirm Docker image builds and runs basic validation successfully.
6. Update `docs/CHANGELOG.md` for all user-visible changes.

## Release notes

For user-visible changes, add an entry to [CHANGELOG.md](CHANGELOG.md).
