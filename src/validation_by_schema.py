"""JSON Schema validation helpers for YAML configuration files.

This module validates YAML files against a JSON Schema document.
Schema can be provided in JSON or YAML format. The validator supports
both a single YAML file path and a directory path (recursive lookup).
"""

from loguru import logger

import json
from typing import Any
from pathlib import Path
from collections.abc import Sequence

import yaml
import jsonschema

from src.utils import _collect_yaml_files, check_for_empty_file
from src.dot_schemas import build_dot_scheme


def _load_schema(schema_file: Path) -> dict[str, Any]:
    """Load schema from JSON/YAML file and return mapping object."""
    schema_text = schema_file.read_text(encoding="utf-8")
    is_yaml_schema = schema_file.suffix.lower() in (".yml", ".yaml")
    loaded = yaml.safe_load(
        schema_text) if is_yaml_schema else json.loads(schema_text)

    if not isinstance(loaded, dict):
        raise jsonschema.SchemaError("Schema root must be a JSON object")

    return loaded


def _validate_single_yaml(yaml_file: Path, schema: dict[str, Any]) -> int:
    """Validate one YAML file against an already loaded schema."""
    try:
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        jsonschema.validate(instance=data, schema=schema)
        logger.info(f"{yaml_file} is valid against schema")
        return 0
    except jsonschema.ValidationError as exc:
        logger.error(
            f"{yaml_file}: {exc.message} at {list(exc.absolute_path)}")
        return 1
    except yaml.YAMLError as exc:
        logger.error(f"YAML parse error in {yaml_file}: {exc}")
        return 1
    except OSError as exc:
        logger.error(f"Failed to read YAML file {yaml_file}: {exc}")
        return 1


def validate_against_schema(yml_path: Path, schema_file: Path) -> int:
    """Validate YAML file(s) against JSON Schema.

    Args:
        yml_path: Path to a YAML file or a directory with YAML files.
        schema_file: Path to schema file in JSON, YML, or YAML format.

    Returns:
        0 if all discovered YAML files are valid.
        1 if at least one file is invalid or an operational error occurs.
    """
    try:
        yaml_files = _collect_yaml_files(yml_path)
        if not yaml_files:
            logger.error(
                f"No YAML files found for schema validation in '{yml_path}'")
            return 1

        if not schema_file.exists():
            logger.error(f"Schema file does not exist: {schema_file}")
            return 1

        schema = _load_schema(schema_file)
        errors = 0

        for file_path in yaml_files:
            # Shared pre-check step: keep behavior aligned with validation_main.
            errors += check_for_empty_file(file_path)
            if errors > 0:
                continue

            errors += _validate_single_yaml(yaml_file=file_path, schema=schema)

        return 0 if errors == 0 else 1

    except jsonschema.SchemaError as exc:
        logger.error(f"Invalid schema: {exc.message}")
        return 1
    except json.JSONDecodeError as exc:
        logger.error(f"Schema JSON parse error in {schema_file}: {exc}")
        return 1
    except yaml.YAMLError as exc:
        logger.error(f"Schema YAML parse error in {schema_file}: {exc}")
        return 1
    except OSError as exc:
        logger.error(f"Failed to read schema file {schema_file}: {exc}")
        return 1
    except Exception as exc:
        logger.error(f"Unexpected error during schema validation: {exc}")
        return 1


def validate_custom_pipeline(
    cfg_files: Sequence[Path],
    val_schema: Path,
    yml2dot_exe: Path,
    job_name: str | None = None,
    output_format: str = "svg"
) -> int:
    """Run schema-based validation pipeline and then build diagrams.

    Args:
        cfg_files: Path to one YAML file or directory with YAML files.
        val_schema: Path to JSON/YAML schema used for validation.
        yml2dot_exe: Path to the `yml2dot` executable.

    Returns:
        0 when schema validation and diagram generation succeed.
        1 when schema validation fails or diagram generation fails.
    """
    if len(cfg_files) > 1:
        logger.error(
            f"custom validation requires exactly one config file, got {len(cfg_files)}")
        return 1

    if not cfg_files:
        logger.error("custom validation requires at least one config file")
        return 1

    cfg_file = cfg_files[0]

    res = validate_against_schema(yml_path=cfg_file, schema_file=val_schema)
    if res != 0:
        logger.error("Validation against schema failed!")
        return 1

    output_file = build_dot_scheme(
        cfg_files=_collect_yaml_files(cfg_file),
        yml2dot_exec=yml2dot_exe,
        job_name=job_name,
        output_format=output_format,
    )
    if output_file is not None:
        logger.info(
            f"Successfully built dot schema, check results: {output_file}")
        logger.success("Pipeline finished successfully!")
        return 0

    logger.warning("Pipeline finished with fail")
    return 1
