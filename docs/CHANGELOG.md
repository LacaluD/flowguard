# Changelog

## [Released]

## [1.0.0] - 2026-05-30

### Added
- Docker support with multi-stage build
- Separate dev and prod requirements files

### Changed
- Refactored validation logic into `ValidationPipeline` and `SchemaValidator` classes

## [Unreleased]
### Added
- JSON and TOML input support alongside YAML
- Per-job graph visualization via `--job` flag
- `--exclude-dir` argument for skipping directories in recursive search

## [0.0.3] - 2026-05-29

### Fixed
- Organized special exception logging funcs in dackend
- Added comprehensive test
- Added support for JSON and TOML input formats
- Introduced per-job

## [0.0.2] - 2026-05-28

### Fixed
- Orphaned nodes in diff graph for removed keys
- False positive on deprecated GitHub Actions version matching (`@v1` no longer matches `@v1.4.0`)

### Added
- CI-friendly exit codes
- JSON Schema validation
- Batch mode and recursive directory search
- Diff visualization with added/removed/changed highlighting
- Golden integration tests
- Corner-case YAML tests (Unicode, BOM, CRLF)
- Coverage threshold enforcement in CI