"""CLI entry point for the YAML validation and diagram generation pipeline.

The script validates one YAML file or an entire directory of YAML files with
`yq`, then optionally generates PNG diagrams using `yml2dot` + Graphviz `dot`.
Executable discovery is performed automatically and can be extended with a
user-provided search directory.
"""

from version import __version__, __build__, __commit__
from src.platform_checks import find_executable, find_executable_recursive
from src.validation_by_schema import validate_against_schema
from src.main_validation_logic import regular_validation
from src.diff_visualizer import visualize_cfgs
from src.cli_parser import _build_parser
from src.logger import MainLogger
import sys
import logging

logger = logging.getLogger(__name__)


def main() -> int:
    """Run the validation pipeline and return a process exit code."""
    args = _build_parser().parse_args()
    MainLogger().init_logger(quiet=getattr(args, "quiet", False))

    # log what version and build is currently running
    logger.info(
        f"Starting YMLValidator {__version__} (build {__build__}, commit {__commit__})"
    )
    input_files = args.files
    difference = getattr(args, "difference", False)

    yq_filename = "yq.exe" if sys.platform == "win32" else "yq"
    yml2_filename = "yml2dot.exe" if sys.platform == "win32" else "yml2dot"
    dot_filename = "dot.exe" if sys.platform == "win32" else "dot"

    # Start with a quick PATH/common-locations lookup.
    yq_exe = find_executable(yq_filename)
    yml2_dot_exe = find_executable(yml2_filename)
    dot_exe = find_executable(dot_filename) if difference else None

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
        if difference and not dot_exe:
            dot_exe = find_executable_recursive(
                fname=dot_filename, search_dir=args.exec_dir
            )

    if not yq_exe or not yml2_dot_exe or (difference and not dot_exe):
        logger.error("Not all required executables were found")
        logger.error("yq: %s", yq_exe)
        logger.error("yml2dot: %s", yml2_dot_exe)
        if difference:
            logger.error("dot: %s", dot_exe)
        return 1

    logger.info("All required executables were found")
    logger.info("yq: %s", yq_exe)
    logger.info("yml2dot: %s", yml2_dot_exe)
    if difference:
        logger.info("dot: %s", dot_exe)

    if args.schema:
        logger.info("Launching validation process with schema")
        return validate_against_schema(yml_path=input_files, schema_file=args.schema)
    elif not args.schema and not difference:
        logger.info("Launching validation process without schema")
        return regular_validation(
            yml_files=input_files, yq_exe=yq_exe, yml2dot_exe=yml2_dot_exe
        )

    if difference:
        logger.info("Building config difference visualization...")
        files_for_diff = input_files if isinstance(
            input_files, list) else [input_files]
        return visualize_cfgs(
            files=files_for_diff,
            difference=difference,
            output_format=getattr(args, "output_format", "svg"),
            dot_exec=dot_exe,
        )


if __name__ == "__main__":
    sys.exit(main())
