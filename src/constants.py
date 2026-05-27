"""Project-wide constants for YAML validation rules and default locations.

This module keeps static values in one place to avoid duplication and to make
future configuration extraction straightforward.
"""

from typing import Final

INDENT_SIZE: Final[int] = 2
EXTENDED_CHECKS: Final[list[str]] = [
    ".name",
    ".jobs",
    ".on",
    ".jobs.*.steps",
    ".jobs.*.runs-on",
]

DEPRECATED_ACTIONS: Final[list[str]] = [
    "setup-python@v3",
    "checkout@v4",
    "telegram-action@v1",
]
