# flowguard

[![CI](https://img.shields.io/github/actions/workflow/status/LacaluD/YML-Validator-Scheme-converter/security_audit.yml?branch=main&label=CI)](https://github.com/LacaluD/YML-Validator-Scheme-converter/actions/workflows/security_audit.yml)
[![Coverage](https://codecov.io/gh/LacaluD/YML-Validator-Scheme-converter/graph/badge.svg?branch=main)](https://codecov.io/gh/LacaluD/YML-Validator-Scheme-converter)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

flowguard is a CLI tool for configuration validation and structure visualization.

It helps teams:
- validate YAML files in CI with predictable exit codes,
- enforce required and optional checks via yq expressions,
- validate against JSON Schema,
- generate visual graphs from YAML configs and config diffs.

## What flowguard does

flowguard is designed for repositories where configuration quality directly impacts delivery reliability.
It combines three layers of protection in one command:

1. Syntax and structural validation:
Checks YAML syntax and required fields with yq expressions, plus optional consistency checks.

2. Contract validation:
Validates files against JSON Schema to enforce domain rules and catch incompatible config changes early.

3. Visualization:
Builds graph outputs from YAML configs and from config-to-config diffs to simplify review and debugging.

In practice, flowguard is useful as:
- a pre-commit or pre-push local validator,
- a CI quality gate for pull requests,
- a troubleshooting helper when changing workflows, pipelines, or deployment manifests.

Key operational behavior:
- deterministic exit codes (0 success, 1 failure),
- `--quiet` mode for cleaner CI logs,
- separation of warning/error output and regular output,
- automatic external binary discovery with optional recursive fallback in custom directories.

## Demo

![flowguard demo](docs/assets/demo.gif)

## Core capabilities

- Validate one file or recursively process a directory
- Run required and optional yq checks over YAML structure
- Detect deprecated GitHub Actions references
- Validate indentation and whitespace issues
- Validate YAML against JSON Schema
- Build diagrams from YAML via yml2dot and Graphviz
- Build config difference graphs in svg, png, or dot format
- Discover external binaries automatically, with optional recursive search in custom folder

## Requirements

Python:
- Python 3.10+
- PyYAML
- jsonschema
- loguru

External tools:
- yq
- yml2dot
- Graphviz dot

## Installation

### 1. Clone repository

```bash
git clone https://github.com/LacaluD/YML-Validator-Scheme-converter.git
cd YML-Validator-Scheme-converter
```

### 2. Create virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

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
# install yml2dot from release page and add it to PATH
```

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y yq graphviz
# install yml2dot from release page and add it to PATH
```

Windows:
- Install yq
- Install Graphviz
- Install yml2dot
- Ensure yq, yml2dot, dot are available in PATH

Quick check:

```bash
command -v yq
command -v yml2dot
command -v dot
```

## CLI usage

Basic validation:

```bash
python main.py --files demo/demo_small_v2.yml
```

Directory validation:

```bash
python main.py --files .
```

Validation with recursive binary fallback directory:

```bash
python main.py --files . --exec-dir /path/to/tools
```

Schema validation pipeline:

```bash
python main.py --files schema_examples/schema_example_valid.yml --schema schema_examples/schema_example.json
```

Disable optional checks:

```bash
python main.py --files demo/demo_small_v2.yml --no-optional-checks
```

Difference visualization:

```bash
python main.py --files demo/demo_small.yml demo/demo_small_v2.yml --difference --output-format svg
```

Quiet mode:

```bash
python main.py --quiet --files demo/demo_small_v2.yml
```

Help commands:

```bash
python main.py --list-checks
python main.py --description
python main.py --version
```

## Exit codes

- 0: success
- 1: validation or runtime failure

This behavior is designed for CI-friendly pipeline integration.

## Logging

flowguard uses loguru with three sinks:
- stderr for warning and error logs
- stdout for debug/info/success logs
- rotating file logs in logs/main.log (configurable)

Environment variables:
- LOG_LEVEL
- LOG_FILE_LEVEL
- EXTERNAL_LOG_LEVEL
- LOG_DIR
- LOG_FILE_NAME

Example:

```bash
export LOG_LEVEL=DEBUG
export LOG_FILE_LEVEL=INFO
export LOG_DIR=./logs
export LOG_FILE_NAME=validator.log
python main.py --files demo/demo_small_v2.yml
```

## Schema guide

See [docs/schema_guide.md](docs/schema_guide.md) for writing and applying custom schemas.

## Testing

Run all tests:

```bash
python -m pytest -q -c configs/pytest.ini
```

Run with coverage:

```bash
python -m coverage run -m pytest -q -c configs/pytest.ini
python -m coverage report --fail-under=90
```

Run golden tests:

```bash
python -m pytest -q tests/test_golden.py -c configs/pytest.ini
```

Update golden baselines:

```bash
python -m pytest -q tests/test_golden.py -c configs/pytest.ini --update-golden
```

## Common errors

| Message | Typical cause | Fix |
|---|---|---|
| '<path>' is neither a file nor directory | Wrong --files path | Check path and rerun |
| No YAML files found | Empty folder or no .yml/.yaml files | Point --files to valid file/folder |
| Not all required executables were found | Missing yq, yml2dot, or dot | Install missing binaries or pass --exec-dir |
| Additional properties are not allowed (True was unexpected) | Unquoted on key parsed as boolean in YAML | Use "on" key in config/schema |

## Project layout

```text
.
├─ main.py
├─ src/
│  ├─ cli_parser.py
│  ├─ constants.py
│  ├─ logger.py
│  ├─ main_validation_logic.py
│  ├─ diff_visualizer.py
│  ├─ validation_by_schema.py
│  ├─ platform_checks.py
│  └─ utils.py
├─ tests/
├─ configs/
├─ docs/
└─ schema_examples/
```

## Status

Implemented:
- CI-friendly output and exit codes
- JSON Schema validation
- Batch mode and recursive search
- Golden integration tests
- Corner-case YAML tests (Unicode, BOM, CRLF, indentation)
- Coverage threshold in CI

Planned:

- Better graph features for specific jobs/sections
- Relationship-focused visualization
- Additional output/reporting improvements

- visualize per-job graphs and inter-job dependencies,
- render YAML anchors, references, and nested relationships,
- supports YAML and JSON as input formats.
