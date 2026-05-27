"""Command-line argument parser configuration for the validator CLI."""

import argparse
from pathlib import Path


class _CompatArgumentParser(argparse.ArgumentParser):
    """ArgumentParser with backward-compatible normalization of `files`.

    If a single file is passed, `files` is unwrapped to `Path` to preserve
    legacy behavior expected by the main validation pipeline and tests.
    """

    def parse_args(self, args=None, namespace=None):  # type: ignore[override]
        parsed = super().parse_args(args=args, namespace=namespace)
        files = getattr(parsed, "files", None)
        if isinstance(files, list) and len(files) == 1:
            parsed.files = files[0]
        return parsed


def _build_parser() -> argparse.ArgumentParser:
    """Create and return the top-level CLI parser."""
    parser = _CompatArgumentParser(description="Run YML Validator")
    parser.add_argument(
        "--exec-dir",
        type=Path,
        help="select dir to find binaries from",
    )
    parser.add_argument(
        "--files", "-f",
        dest="files",
        type=Path,
        required=True,
        nargs="+",
        help="choose dir or file path to configs",
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
    parser.add_argument(
        "--difference", "-diff",
        action="store_true",
        help="build svg image of difference between 2 configs",
    )
    parser.add_argument(
        "--output-format", "-o",
        choices=("svg", "png", "dot"),
        default="svg",
        help="output format for diff graph",
    )

    return parser
