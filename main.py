"""CLI entry point for the YAML validation and diagram generation pipeline.

The script validates one YAML file or an entire directory of YAML files with
`yq`, then optionally generates PNG diagrams using `yml2dot` + Graphviz `dot`.
Executable discovery is performed automatically and can be extended with a
user-provided search directory.
"""

import sys
import logging

logger = logging.getLogger(__name__)

from src.logger import MainLogger
from src.cli_parser import _build_parser
from src.main_validation_logic import regular_validation
from src.validation_by_schema import validate_against_schema
from src.platform_checks import find_executable, find_executable_recursive

from version import __version__, __build__, __commit__


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
        return validate_against_schema(yml_path=args.yml_files, schema_file=args.schema)

    logger.info("Launching validation process without schema")
    return regular_validation(
        yml_files=args.yml_files, yq_exe=yq_exe, yml2dot_exe=yml2_dot_exe
    )


if __name__ == "__main__":
    sys.exit(main())
