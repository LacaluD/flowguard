"""CLI entry point for the YAML validation and diagram generation pipeline.

The script validates one config file or an entire directory of YAML files with
`yq`, then optionally generates PNG diagrams using `yml2dot` + Graphviz `dot`.
Executable discovery is performed automatically and can be extended with a
user-provided search directory.
"""


import sys

from version import __version__, __build__, __commit__
from src.platform_checks import find_executable, find_executable_recursive
from src.validation_by_schema import validate_custom_pipeline
from src.main_validation_logic import regular_validation
from src.diff_visualizer import visualize_cfgs
from src.cli_parser import _build_parser, show_list_checks, show_description, show_version
from src.logger import MainLogger


def main() -> int:
    """Run the validation pipeline and return a process exit code."""
    args = _build_parser().parse_args()
    logger = MainLogger().init_logger(quiet=getattr(args, "quiet", False))

    # log what version and build is currently running
    logger.info(
        f"Starting flowguard {__version__} (build {__build__}, commit {__commit__})"
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

    if args.list_checks:
        return show_list_checks()

    if args.description:
        return show_description()

    if args.version:
        return show_version()

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
        logger.error(f"yq: {yq_exe}")
        logger.error(f"yml2dot: {yml2_dot_exe}")
        if difference:
            logger.error(f"dot: {dot_exe}")
        return 1

    logger.info("All required executables were found")
    logger.info(f"yq: {yq_exe}")
    logger.info(f"yml2dot: {yml2_dot_exe}")
    if difference:
        logger.info(f"dot: {dot_exe}")

    if args.schema:
        logger.info("Launching validation process with schema")
        return validate_custom_pipeline(
            cfg_files=input_files,
            val_schema=args.schema,
            yml2dot_exe=yml2_dot_exe,
        )
    elif not args.schema and not difference:
        logger.info("Launching validation process without schema")
        return regular_validation(
            cfg_files=input_files, yq_exe=yq_exe, yml2dot_exe=yml2_dot_exe, run_optional=not args.no_optional_checks
        )

    if difference:
        if dot_exe is None:
            logger.error("dot executable is missing")
            return 1
        logger.info("Building config difference visualization...")
        files_for_diff = input_files if isinstance(
            input_files, list) else [input_files]
        return visualize_cfgs(
            files=files_for_diff,
            difference=difference,
            output_format=getattr(args, "output_format", "svg"),
            dot_exec=dot_exe,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
