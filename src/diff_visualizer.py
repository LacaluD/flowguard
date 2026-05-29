"""Build and render a visual diff between two configuration files.

The module provides a small CLI that compares two files (`.yml`, `.yaml`,
`.json`, `.toml`) and generates a graph (`.svg`, `.png`, or raw `.dot`).

The graph highlights:
- added keys,
- removed keys,
- changed values,
- unchanged nodes.
"""

from __future__ import annotations
import tomllib
import yaml
import json
from typing import Any, Literal
from pathlib import Path
from collections.abc import Mapping, Sequence
import subprocess
import hashlib

from loguru import logger
from src.utils import _extract_job_view

SUPPORTED_EXT = {".yml", ".yaml", ".json", ".toml"}
DIFF_COLORS: dict[str, str] = {
    "added": "#ccffcc",
    "removed": "#ffcccc",
    "changed": "#ffffcc",
    "default": "#fafafa",
}

OutputFormat = Literal["svg", "png", "dot"]


def _safe_job_filename(job_name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in job_name)


def _build_output_paths(
    sec_file: Path,
    output_format: OutputFormat,
    job_name: str | None = None,
) -> tuple[Path, Path]:
    """Build unique output paths for the DOT source and rendered artifact."""
    if job_name:
        job_suffix = _safe_job_filename(job_name)
        dot_file = sec_file.with_name(
            f"{sec_file.stem}.job-{job_suffix}.diff.dot")
        output_file = sec_file.with_name(
            f"{sec_file.stem}.job-{job_suffix}.diff.{output_format}"
        )
        return dot_file, output_file

    dot_file = sec_file.with_name(f"{sec_file.stem}.diff.dot")
    output_file = sec_file.with_name(f"{sec_file.stem}.diff.{output_format}")
    return dot_file, output_file


def _parse_yml(file_path: Path) -> Any:
    """Read and parse a YAML file.

    Args:
        file_path: Path to a YAML file.

    Returns:
        Parsed YAML object. If the YAML file is empty, returns an empty dict.
    """
    with file_path.open(encoding="utf-8") as file_obj:
        data = yaml.safe_load(file_obj)
    return {} if data is None else data


def _parse_json(file_path: Path) -> Any:
    """Read and parse a JSON file.

    Args:
        file_path: Path to a JSON file.

    Returns:
        Parsed JSON object.
    """
    with file_path.open(encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _parse_toml(file_path: Path) -> Any:
    """Read and parse a TOML file.

    Args:
        file_path: Path to a TOML file.

    Returns:
        Parsed TOML object.
    """
    with file_path.open("rb") as file_obj:
        return tomllib.load(file_obj)


def _parse_file(file_path: Path) -> Any:
    """Read and parse a supported config file.

    Supported formats are YAML (`.yml`, `.yaml`), JSON (`.json`), and
    TOML (`.toml`).
    Extension matching is case-insensitive.

    Args:
        file_path: Path to input config file.

    Returns:
        Parsed file object.

    Raises:
        ValueError: If file extension is not supported.
    """
    match file_path.suffix.lower():
        case ".yml" | ".yaml":
            return _parse_yml(file_path)
        case ".json":
            return _parse_json(file_path)
        case ".toml":
            return _parse_toml(file_path)
        case _:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")


def _flatten(data: Any, prefix: str = "") -> dict[str, str]:
    """Flatten nested mappings/sequences into dot-separated keys.

    Example:
        {"a": {"b": 1}, "c": [10]} -> {"a.b": "1", "c.0": "10"}

    Args:
        data: YAML-like structure (mapping, list, or scalar).
        prefix: Current key prefix used during recursion.

    Returns:
        Flat dictionary where keys are dot-separated paths and values are strings.
    """
    result: dict[str, str] = {}
    if isinstance(data, Mapping):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, (Mapping, list)):
                result.update(_flatten(value, full_key))
            else:
                result[full_key] = str(value)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            full_key = f"{prefix}.{index}" if prefix else str(index)
            if isinstance(item, (Mapping, list)):
                result.update(_flatten(item, full_key))
            else:
                result[full_key] = str(item)
    return result


def _get_diff(
    first_flat: Mapping[str, str], second_flat: Mapping[str, str]
) -> tuple[set[str], set[str], set[str]]:
    """Return key sets for added, removed, and changed paths.

    Args:
        first_flat: Flattened representation of the old config.
        second_flat: Flattened representation of the new config.

    Returns:
        Tuple (added, removed, changed).
    """
    added = second_flat.keys() - first_flat.keys()
    removed = first_flat.keys() - second_flat.keys()
    changed = {
        key
        for key in first_flat.keys() & second_flat.keys()
        if first_flat[key] != second_flat[key]
    }

    logger.info("Config difference visualization saved successfully")
    return added, removed, changed


def _escape_label(value: Any) -> str:
    """Escape value for safe insertion into Graphviz node labels."""
    return str(value).replace('"', '\\"')


def _build_dot(
    data: Any,
    fst_flat: Mapping[str, str],
    added: set[str],
    removed: set[str],
    changed: set[str],
    label: str = "diff",
) -> str:
    """Build Graphviz DOT source that visualizes config differences.

    Args:
        data: Parsed YAML object for the newer config.
        fst_flat: Flattened representation of the older config.
        added: Added key paths.
        removed: Removed key paths.
        changed: Changed key paths.
        label: Graph title.

    Returns:
        A complete DOT graph as string.
    """
    lines = [
        "digraph {",
        f'  label="{label}"',
        "  labelloc=t",
        '  fontname="Fira Mono"',
        "  fontsize=14",
        '  rankdir="LR"',
        '  node [shape=box style="rounded,filled" fillcolor="#fafafa" fontname="Fira Mono" fontsize=10 penwidth=2]',
        "  edge [arrowhead=none penwidth=2]",
    ]

    def node_id(key: str) -> str:
        """Build a stable DOT node identifier from a key path."""
        safe = key.replace(".", "_").replace("-", "_").replace(" ", "_")
        suffix = hashlib.md5(
            key.encode(), usedforsecurity=False).hexdigest()[:6]
        return f"{safe}_{suffix}"

    def classify(key: str) -> str:
        """Classify a key path by diff status."""
        if key in added:
            return "added"
        if key in removed:
            return "removed"
        if key in changed:
            return "changed"
        return "default"

    def walk_node(full_key: str, value: Any, parent_key: str | None = None) -> None:
        """Recursively render a YAML node and its children."""
        nid = node_id(full_key)
        color = DIFF_COLORS[classify(full_key)]
        label_text = _escape_label(full_key.split(".")[-1])

        lines.append(f'  {nid} [label="{label_text}" fillcolor="{color}"]')

        if parent_key is not None:
            lines.append(f"  {node_id(parent_key)} -> {nid}")

        if isinstance(value, Mapping):
            for child_key, child_value in value.items():
                child_full_key = f"{full_key}.{child_key}"
                walk_node(child_full_key, child_value, full_key)
            return

        if isinstance(value, list):
            for index, item in enumerate(value):
                item_key = f"{full_key}.{index}"
                walk_node(item_key, item, full_key)
            return

        val_key = f"{full_key}.__val__"
        val_nid = node_id(val_key)
        val_label = _escape_label(value)
        val_color = DIFF_COLORS[classify(full_key)]
        lines.append(
            f'  {val_nid} [label="{val_label}" fillcolor="{val_color}"]')
        lines.append(f"  {nid} -> {val_nid}")

    if isinstance(data, Mapping):
        for key, value in data.items():
            full_key = str(key)
            walk_node(full_key, value)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            full_key = str(index)
            walk_node(full_key, item)
    else:
        walk_node("root", data)

    # Add removed keys that are present only in the old file.
    for key in sorted(removed):
        nid = node_id(key)
        val_label = _escape_label(fst_flat[key])
        key_label = _escape_label(key.split(".")[-1])
        lines.append(
            f'  {nid} [label="{key_label}" fillcolor="{DIFF_COLORS["removed"]}"]'
        )

        parent = ".".join(key.split(".")[:-1])
        if parent:
            lines.append(f"  {node_id(parent)} -> {nid}")

        val_nid = node_id(f"{key}.__val__")
        lines.append(
            f'  {val_nid} [label="{val_label}" fillcolor="{DIFF_COLORS["removed"]}"]'
        )
        lines.append(f"  {nid} -> {val_nid}")

    lines.extend(_build_legend())
    lines.append("}")
    return "\n".join(lines)


def _build_legend() -> list[str]:
    """Build legend lines for the DOT graph."""
    return [
        "  subgraph cluster_legend {",
        '    label="Legend"',
        '    fontname="Fira Mono"',
        "    fontsize=13",
        '    style="rounded,filled"',
        '    fillcolor="#f5f5f5"',
        '    color="#cccccc"',
        '    rank="same"',
        '    legend_added    [label="+  added"     fillcolor="#ccffcc" style="rounded,filled" fontname="Fira Mono" fontsize=11]',
        '    legend_changed  [label="~  changed"   fillcolor="#ffffcc" style="rounded,filled" fontname="Fira Mono" fontsize=11]',
        '    legend_removed  [label="x  removed"   fillcolor="#ffcccc" style="rounded,filled" fontname="Fira Mono" fontsize=11]',
        '    legend_default  [label="   unchanged" fillcolor="#fafafa" style="rounded,filled" fontname="Fira Mono" fontsize=11]',
        '    legend_added -> legend_changed -> legend_removed -> legend_default [style="invis"]',
        "  }",
    ]


def get_cfg_difference(
    fst_file: Path,
    sec_file: Path,
    dot_exec: Path,
    output_format: OutputFormat = "svg",
    job_name: str | None = None,
) -> int:
    """Generate diff graph for two supported config files.

    Args:
        fst_file: Path to old/original config file.
        sec_file: Path to new config file.
        output_format: Output format for generated graph (svg, png, dot).

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    logger.info(
        f"Got file formats: {fst_file.suffix}, {sec_file.suffix}. Output format: {output_format}"
    )
    fst_data = _parse_file(fst_file)
    sec_data = _parse_file(sec_file)

    # Fst must contain a job (otherwise there is nothing to compare), sec - optional (job could be deleted).
    if job_name:
        missing = []
        try:
            fst_data = _extract_job_view(
                fst_data, job_name=job_name, file_path=fst_file)
        except ValueError:
            missing.append(str(fst_file))
        try:
            sec_data = _extract_job_view(
                sec_data, job_name=job_name, file_path=sec_file)
        except ValueError:
            logger.warning(
                f"job '{job_name}' not found in {sec_file}, treating as removed")
            sec_data = {"jobs": {}}
        if missing:
            logger.error(
                f"job '{job_name}' not found in: {', '.join(missing)}")
            return 1

    fst_flat = _flatten(fst_data)
    sec_flat = _flatten(sec_data)

    added, removed, changed = _get_diff(fst_flat, sec_flat)

    dot_source = _build_dot(
        sec_data,
        fst_flat,
        added,
        removed,
        changed,
        label=f"{fst_file.name} vs {sec_file.name}",
    )
    logger.info("Successfully built dot vizualization")

    dot_file, output_file = _build_output_paths(
        sec_file=sec_file,
        output_format=output_format,
        job_name=job_name,
    )

    dot_file.write_text(dot_source, encoding="utf-8")

    if output_format == "dot":
        logger.info(f"dot saved: {dot_file}")
        return 0

    result = subprocess.run(
        [dot_exec, f"-T{output_format}",
            str(dot_file), "-o", str(output_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error(f"dot STDERR: {result.stderr}")
        dot_file.unlink(missing_ok=True)
        return 1

    logger.debug(f"dot task finished with returcode:{result.returncode}")

    dot_file.unlink(missing_ok=True)
    logger.info(f"{output_format} saved: {output_file}")
    return 0


def visualize_cfgs(
    files: Sequence[Path],
    dot_exec: Path,
    difference: bool = False,
    output_format: OutputFormat = "svg",
    job_name: str | None = None,
) -> int:
    """Entrypoint for CLI execution.

    Args:
        files: Input YAML, JSON, or TOML files.
        difference: If True, build diff graph for exactly two files.
        output_format: Output format for generated graph.

    Returns:
        Process exit code.
    """
    if not difference:
        logger.warning("No action specified. Use --difference.")
        return 0

    if len(files) != 2:
        logger.warning("--difference requires exactly 2 files")
        return 1

    if not all(file_path.suffix.lower() in SUPPORTED_EXT for file_path in files):
        logger.error(
            "Wrong file format! Both files must be .yml, .yaml, .json, or .toml"
        )
        return 1

    return get_cfg_difference(
        files[0],
        files[1],
        output_format=output_format,
        dot_exec=dot_exec,
        job_name=job_name,
    )
