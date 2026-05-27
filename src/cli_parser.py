"""Command-line argument parser configuration for the validator CLI."""

import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    """Create and return the top-level CLI parser."""
    parser = argparse.ArgumentParser(description="Run YML Validator")
    parser.add_argument(
        "--exec-dir",
        type=Path,
        help="select dir to find binaries from",
    )
    parser.add_argument(
        "--yml-files",
        type=Path,
        required=True,
        help="choose dir or file path to yml configs",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="suppress output",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        help="path to JSON Schema file (.json or .yml)",
    )

    return parser
