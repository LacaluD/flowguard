"""CLI entry point for the YAML validation and diagram generation pipeline.

The script validates one YAML file or an entire directory of YAML files with
`yq`, then optionally generates PNG diagrams using `yml2dot` + Graphviz `dot`.
Executable discovery is performed automatically and can be extended with a
user-provided search directory.
"""

import logging
import sys
from pathlib import Path

from src.cli_parser import _build_parser
from src.main_validation_logic import validation_main, build_dot_scheme
from src.logger import MainLogger
from src.platform_checks import find_executable, find_executable_recursive
from src.validation_by_schema import validate_against_schema

from version import __version__

__build__ = "__dev__"
__commit__ = "__dev__"


logger = logging.getLogger(__name__)


def main() -> int:
    """Run the validation pipeline and return a process exit code."""
    args = _build_parser().parse_args()
    MainLogger().init_logger(quiet=getattr(args, "quiet", False))

    # log what version and build is currently running
    logger.info(
        f"Starting YMLValidator {__version__} (build {__build__}, commit {__commit__})"
    )

    yq_filename = "yq.exe" if sys.platform == "win32" else "yq"
    yml2_filename = "yml2dot.exe" if sys.platform == "win32" else "yml2dot"

    # Start with a quick PATH/common-locations lookup.
    yq_exe = find_executable(yq_filename)
    yml2_dot_exe = find_executable(yml2_filename)

    # If a custom directory is provided, perform recursive fallback search.
    if args.exec_dir:
        if not yq_exe:
            yq_exe = find_executable_recursive(
                fname=yq_filename, search_dir=args.exec_dir
            )
        if not yml2_dot_exe:
            yml2_dot_exe = find_executable_recursive(
                fname=yml2_filename, search_dir=args.exec_dir
            )

    if not yq_exe or not yml2_dot_exe:
        logger.error("Not all required executables were found")
        logger.error("yq: %s", yq_exe)
        logger.error("yml2dot: %s", yml2_dot_exe)
        return 1

    logger.info("All required executables were found")
    logger.info("yq: %s", yq_exe)
    logger.info("yml2dot: %s", yml2_dot_exe)

    if args.schema:
        logger.info("Launching validation process with schema")
        res = validate_against_schema(yml_path=args.yml_files, schema_file=args.schema)
        if res != 0:
            return 1

    logger.info("Launching validation process without schema")
    validated = validation_main(yml_path=args.yml_files, yq_exec=yq_exe)
    if not validated:
        logger.error("Validation failed")
        return 1

    output_file = build_dot_scheme(yml_files=validated, yml2dot_exec=yml2_dot_exe)
    if output_file is not None:
        logger.info("Pipeline ended successfully, check results: %s", output_file)
        return 0

    logger.error("Diagram generation failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
