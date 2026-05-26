# Project Goal

[![CI](https://img.shields.io/github/actions/workflow/status/LacaluD/YML-Validator-Scheme-converter/security_audit.yml?branch=main&label=CI)](https://github.com/LacaluD/YML-Validator-Scheme-converter/actions/workflows/security_audit.yml)
[![Coverage](https://codecov.io/gh/LacaluD/YML-Validator-Scheme-converter/graph/badge.svg?branch=main)](https://codecov.io/gh/LacaluD/YML-Validator-Scheme-converter)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)


YMLValidator is a command-line tool that validates YAML configuration files and builds visual pipeline diagrams.
It helps teams catch broken workflow files early and quickly understand pipeline structure.

## Demo

![YMLValidator demo](docs/assets/demo.gif)

## Features
The project uses [yq](https://github.com/mikefarah/yq) for parsing/validation and [yml2dot](https://github.com/lucasepe/yml2dot) + Graphviz `dot` for diagram generation.

- Validate one YAML file or all YAML files inside a directory (recursive search)
- Run base YAML syntax checks through `yq`
- Run configurable required-field checks (for example `.jobs.*.steps`)
- Detect deprecated GitHub Actions references
- Validate indentation and whitespace formatting rules
- Generate `.png` diagrams from validated YAML files
- Search external binaries automatically and optionally recurse through a custom folder

## Dependencies
Python dependencies:

- Python 3.10+
- `PyYAML` (YAML parsing)
- `jsonschema` (schema-based validation)

External CLI tools:

- `yq` (required)
- `yml2dot` (required)
- `dot` from Graphviz (required for PNG output)

## Installation
### 1. Clone repository
```bash
git clone https://github.com/LacaluD/YML-Validator-Scheme-converter.git
cd YML-Validator-Scheme-converter
```

### 2. Create and activate virtual environment
macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
# or
pip install ".[dev]"
```

### 4. Install external binaries
macOS (Homebrew):
```bash
brew install yq graphviz
```

Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y yq graphviz
```

Windows:

1. Install `yq` from the official release page or package manager.
2. Install [Graphviz](https://graphviz.org/download/).
3. Install [yml2dot](https://github.com/lucasepe/yml2dot/releases) and ensure `yq`, `yml2dot`, and `dot` are available in `PATH`.

### 5. Run tool
Validate one file:
```bash
python main.py --yml-files test.yml
```

Validate all YAML files in directory:
```bash
python main.py --yml-files .
```

Run with additional recursive binary lookup:
```bash
python main.py --yml-files . --exec-dir /path/to/tools
```

Run schema-based validation:
```bash
python main.py --yml-files test.yml --schema schema_examples/example_schema.json
```

## Logging
The project uses Python built-in `logging` with both console and rotating file output.

Default behavior:

- `INFO`/`DEBUG` logs are written to `stdout`
- `WARNING`/`ERROR`/`CRITICAL` logs are written to `stderr`
- With `--quiet`, normal informational console output is suppressed
- File logs are written to `logs/main.log`
- File rotation is enabled via `TimedRotatingFileHandler`

Examples:

macOS/Linux:
```bash
export LOG_LEVEL=DEBUG
export LOG_FILE_LEVEL=INFO
export LOG_DIR=./logs
export LOG_FILE_NAME=validator.log
python main.py --yml-files test.yml
```

Windows PowerShell:
```powershell
$env:LOG_LEVEL = "DEBUG"
$env:LOG_FILE_LEVEL = "INFO"
$env:LOG_DIR = ".\\logs"
$env:LOG_FILE_NAME = "validator.log"
python main.py --yml-files test.yml
```

## Testing
The project test suite is based on `pytest` and covers both business logic and CLI behavior.

Current test coverage includes:

- Unit tests for core validators and utility functions
- Integration tests for the main validation pipeline with mocked external binaries
- Schema-validation tests for valid/invalid schemas and YAML files
- Corner-case tests: Unicode, BOM, CRLF/LF, tabs, mixed indentation, empty values, deeply nested YAML
- CLI output stream checks using `capsys` (`stdout` vs `stderr`)

### Edge Cases

The validator is tested against real-world YAML quirks:

| Case | Behavior |
|------|----------|
| UTF-8 Unicode (Cyrillic, Japanese, etc.) | ✅ Supported |
| BOM (Byte Order Mark) | ✅ Supported |
| CRLF line endings (Windows) | ✅ Supported |
| Tabs instead of spaces | ❌ Rejected (invalid YAML) |
| Mixed indentation | ❌ Rejected (invalid YAML) |
| Empty values (`null`, blank) | ✅ Supported |
| Deeply nested structures (50+ levels) | ✅ Supported |

Run tests locally:
```bash
python -m pytest -q -c configs/pytest.ini
```

Run tests with coverage:
```bash
python -m coverage run -m pytest -q -c configs/pytest.ini
python -m coverage report --fail-under=90
```

Run golden-file checks:
```bash
python -m pytest -q tests/test_golden.py -c configs/pytest.ini
```

Update golden baselines:
```bash
python -m pytest -q tests/test_golden.py -c configs/pytest.ini --update-golden
```

CI notes:

- Test job runs on each push/PR to `main`
- Coverage threshold is configured as `90%` in project coverage settings
- Coverage report is uploaded as a CI artifact

## Project Structure
```text
YMLValidator/
├─ .github/                  # CI workflows
├─ configs/
│  ├─ pytest.ini             # Pytest configuration
│  └─ bandit.yml             # Bandit configuration
├─ main.py                  # CLI entry point
├─ pyproject.toml            # Project metadata and tooling config
├─ README.md
├─ TODO.md                  # Roadmap notes
├─ schema_examples/         # Example JSON schemas
├─ src/
│  ├─ cli_parser.py            # CLI argument parser
│  ├─ constants.py             # Validation constants/config values
│  ├─ logger.py                # Project logging setup
│  ├─ main_validation_logic.py # YAML validation + diagram generation
│  ├─ platform_checks.py       # Cross-platform executable discovery
│  ├─ utils.py                 # Shared file collection and file checks
│  └─ validation_by_schema.py  # JSON Schema validation pipeline
└─ tests/
	├─ conftest.py              # Custom pytest flags (including --update-golden)
	└─ golden/                  # Golden-file inputs/expected outputs
	...
```

## DONE
- Added golden-file integration tests with fixtures in `tests/golden/`
- Added `--update-golden` pytest option to refresh expected snapshots
- Added edge-case test coverage (Unicode, BOM, CRLF/LF, tabs, mixed indentation)

## TODO
- Add configuration file support for validation rules
- Provide packaged releases for Windows/macOS/Linux
- Add smoke integration with real binaries in CI
