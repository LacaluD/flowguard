# Makefile Guide

This project includes a Makefile for common local and CI-like routines.

## Core Targets

| cmd | what it does |
| --- | --- |
| `make run` | Runs the bot: `python main.py` |
| `make install` | Installs runtime requirements from `requirements.txt` |
| `make install-dev` | Installs from `dev-requirements.txt` |

## Docker usage
| cmd | what it does |
| --- | --- |
| `make docker-build` | Build Docker image |
| `make docker-run` | Run container from built image |
| `make docker-stop` | Stop running container |
| `make docker-rm` | Remove stopped container |
| `make docker-clean` | Stop container, remove container and image |

## Tests and Coverage

| cmd | what it does |
| --- | --- |
| `make tests` | Runs: `python -m coverage run -m pytest -v -c configs/pytest.ini` |
| `make tests-build-cov-report` | Runs: `python -m coverage report | tee docs/coverage-report.txt`; intended to be used after `make tests` |

For direct pytest + coverage over `main.py` and `src/*`:

| cmd | what it does |
| --- | --- |
| `python -m pytest src/tests --cov=main --cov=src --cov-report=term-missing` | Direct pytest + coverage run for `main.py` and `src/*` |

## Security

| cmd | what it does |
| --- | --- |
| `make sec-bandit` | Bandit scan with project config; saves report to `docs/bandit-report.txt` |

## Static Analysis and Formatting

| cmd | what it does |
| --- | --- |
| `make lint` | mypy checks for `src/` |
| `make lint-calls` | mypy checks with `call-arg` enabled |
| `make typecheck` | Ruff + Black check mode |
| `make format` | Ruff auto-fix + Black check |

## Housekeeping and Composite Pipeline

| cmd | what it does |
| --- | --- |
| `make clean` | Removes `__pycache__`, `*.pyc`, and coverage artifacts |
| `make ci` | Sequentially runs tests, security checks, formatting checks, and lint |

## Practical Order for Local Validation

| cmd | what it does |
| --- | --- |
| `make install` | Install runtime dependencies |
| `make tests` | Run test suite with coverage collection |
| `make tests-build-cov-report` | Build and save coverage report |
| `make sec-bandit` | Run Bandit security scan |
| `make sec-pip-audit` | Run dependency vulnerability scan |
| `make typecheck` | Run Ruff + Black checks |
| `make lint` | Run mypy checks |
