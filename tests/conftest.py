from pathlib import Path

import pytest

from src import pipeline as pipeline_module
from src import validation_by_schema as schema_module
from src.pipeline import ValidationPipeline
from src.validation_by_schema import SchemaValidator


def pytest_addoption(parser):
    parser.addoption("--update-golden", action="store_true")


def _patch_pipeline_compat() -> None:
    """Expose module-level compatibility wrappers used by older tests."""

    def _materialize_yaml_for_validation(cfg_file: Path) -> Path:
        return ValidationPipeline(
            yq_exe=Path("yq"), excluded_paths=[], run_optional=False
        )._materialize_yaml_for_validation(cfg_file)

    def _normalize_action_ref(ref: str):
        return ValidationPipeline(
            yq_exe=Path("yq"), excluded_paths=[], run_optional=False
        )._normalize_action_ref(ref)

    def check_for_deprecated_keys(file_path: Path, content: str) -> int:
        return ValidationPipeline(
            yq_exe=Path("yq"), excluded_paths=[], run_optional=False
        ).check_for_deprecated_keys(file_path, content)

    def run_yq(
        fpath: Path,
        expression: str,
        description: str,
        yq_exec: Path,
        optional: bool = False,
    ) -> int:
        return ValidationPipeline(
            yq_exe=yq_exec, excluded_paths=[], run_optional=optional
        ).run_yq(fpath=fpath, expression=expression, description=description)

    def check_indentation(file_path: Path) -> int:
        return ValidationPipeline(
            yq_exe=Path("yq"), excluded_paths=[], run_optional=False
        ).check_indentation(file_path)

    def run_yq_in_threadpool(
        fpath: Path,
        yq_exec: Path,
        fending: str,
        run_optional: bool = True,
    ) -> int:
        return ValidationPipeline(
            yq_exe=yq_exec, excluded_paths=[], run_optional=run_optional
        ).run_yq_in_threadpool(fpath=fpath, fending=fending)

    def validate_config(
        yml_path: Path,
        yq_exec: Path,
        excluded_paths: list[Path],
        run_optional: bool = False,
    ) -> int:
        return ValidationPipeline(
            yq_exe=yq_exec,
            excluded_paths=excluded_paths,
            run_optional=run_optional,
        ).validate_config(yml_path=yml_path)

    def _build_job_scoped_validation_yaml(cfg_file: Path, job_name: str) -> Path | None:
        return ValidationPipeline(
            yq_exe=Path("yq"), excluded_paths=[], run_optional=False
        )._build_job_scoped_validation_yaml(cfg_file=cfg_file, job_name=job_name)

    def regular_validation(
        *,
        cfg_files,
        yq_exe: Path,
        excluded_paths,
        yml2dot_exe: Path,
        run_optional: bool = False,
        job_name: str | None = None,
        output_format: str = "svg",
    ) -> int:
        return ValidationPipeline(
            yq_exe=yq_exe,
            excluded_paths=list(excluded_paths),
            run_optional=run_optional,
        ).regular_validation(
            cfg_files=cfg_files,
            yml2dot_exe=yml2dot_exe,
            job_name=job_name,
            output_format=output_format,
        )

    pipeline_module._materialize_yaml_for_validation = _materialize_yaml_for_validation
    pipeline_module._normalize_action_ref = _normalize_action_ref
    pipeline_module.check_for_deprecated_keys = check_for_deprecated_keys
    pipeline_module.run_yq = run_yq
    pipeline_module.check_indentation = check_indentation
    pipeline_module.run_yq_in_threadpool = run_yq_in_threadpool
    pipeline_module.validate_config = validate_config
    pipeline_module._build_job_scoped_validation_yaml = (
        _build_job_scoped_validation_yaml
    )
    pipeline_module.regular_validation = regular_validation


def _patch_schema_compat() -> None:
    """Expose module-level compatibility wrappers used by older tests."""

    def _load_schema(schema_file: Path):
        return SchemaValidator(schema_path=schema_file)._load_schema(schema_file)

    def _validate_single_yaml(yaml_file: Path, schema: dict) -> int:
        return SchemaValidator(schema_path=Path("schema.json"))._validate_single_yaml(
            yaml_file, schema
        )

    def validate_against_schema(yml_path: Path, schema_file: Path) -> int:
        return SchemaValidator(schema_path=schema_file).validate_against_schema(
            yml_path
        )

    def validate_custom_pipeline(
        *,
        cfg_files,
        val_schema: Path,
        yml2dot_exe: Path,
        job_name: str | None = None,
        output_format: str = "svg",
    ) -> int:
        return SchemaValidator(schema_path=val_schema).validate_custom_pipeline(
            cfg_files=cfg_files,
            yml2dot_exe=yml2dot_exe,
            job_name=job_name,
            output_format=output_format,
        )

    schema_module._load_schema = _load_schema
    schema_module._validate_single_yaml = _validate_single_yaml
    schema_module.validate_against_schema = validate_against_schema
    schema_module.validate_custom_pipeline = validate_custom_pipeline


@pytest.fixture(autouse=True, scope="session")
def patch_legacy_test_api() -> None:
    _patch_pipeline_compat()
    _patch_schema_compat()
