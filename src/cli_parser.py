"""Command-line argument parser configuration for the validator CLI."""

import sys
import argparse
from collections.abc import Sequence
from pathlib import Path

from src.constants import OPTIONAL_CHECKS, EXTENDED_CHECKS, PROJECT_DESCRIPTION
from version import __build__, __commit__, __version__


class _CompatArgumentParser(argparse.ArgumentParser):
    """ArgumentParser with backward-compatible normalization of `files`.

    If a single file is passed, `files` is unwrapped to `Path` to preserve
    legacy behavior expected by the main validation pipeline and tests.
    """

    def parse_args(  # type: ignore[override]
        self,
        args: Sequence[str] | None = None,
        namespace: argparse.Namespace | None = None,
    ) -> argparse.Namespace:
        parsed = super().parse_args(args=args, namespace=namespace)
        files = getattr(parsed, "files", None)
        if isinstance(files, list) and len(files) == 1:
            parsed.files = files[0]
        return parsed


def _build_parser() -> argparse.ArgumentParser:
    """Create and return the top-level CLI parser."""
    parser = _CompatArgumentParser(
        description="Run flowguard: YAML validation and visualization CLI"
    )
    parser.add_argument(
        "--exec-dir",
        type=Path,
        help="select dir to find binaries from",
    )
    parser.add_argument(
        "--files",
        "-f",
        dest="files",
        type=Path,
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
        "--difference",
        "-diff",
        action="store_true",
        help="build svg image of difference between 2 configs",
    )
    parser.add_argument(
        "--output-format",
        "-o",
        choices=("svg", "png", "dot"),
        default="svg",
        help="output format for difference graph",
    )
    parser.add_argument(
        "--no-optional-checks",
        action="store_true",
        help="run YQ without optional check. Run --list-checks to list all available checks",
    )
    parser.add_argument(
        "--list-checks", action="store_true", help="list all available checks and exit"
    )
    parser.add_argument(
        "--description", action="store_true", help="show program description and exit"
    )
    parser.add_argument(
        "--version", action="store_true", help="show program's version number and exit"
    )

    return parser


def show_list_checks() -> int:
    print("Required checks:")
    for expr in EXTENDED_CHECKS:
        print(f"  {expr}")
    print("\nOptional checks (disable with --no-optional-checks):")
    for expr in OPTIONAL_CHECKS:
        print(f"  {expr}")
    return 0


def show_description() -> int:
    print(PROJECT_DESCRIPTION)
    return 0


def show_version() -> int:
    print(f"flowguard {__version__} (build {__build__}, commit {__commit__})")
    return 0
