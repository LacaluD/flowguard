"""Project-wide constants for YAML validation rules and default locations.

This module keeps static values in one place to avoid duplication and to make
future configuration extraction straightforward.
"""

from typing import Final

INDENT_SIZE: Final[int] = 2


EXTENDED_CHECKS: Final[list[str]] = [
    # obligatory
    ".name",
    ".on",
    ".jobs",
    # obligatory inside job
    '.jobs[]."runs-on"',
    ".jobs[].steps",
    # each step must have either "run" or "uses" — but yq can't express "or" logic,
    # so adding both to the list would produce false positives
    # when only one of them is present
    # checking values
    ".name | length > 0",  # name not empty
    ".jobs | keys | length > 0",  # at least one job
    ".jobs[].steps | length > 0",  # steps on empty array
    '.jobs[]."runs-on" | select(. != null)',  # runs-on not null
]

OPTIONAL_CHECKS: Final[list[str]] = [
    # optionals — check only if field exists
    '.jobs[]."timeout-minutes" | select(. != null) | select(. > 0)',
    ".on.schedule // null | select(. != null) | .[].cron | select(. != null)",
    ".jobs[].needs | select(. != null) | length > 0",
]


# EXTENDED_CHECKS: Final[list[str]] = [
#     # obligatory
#     ".name",
#     ".on",
#     ".jobs",

#     # obligatory inside job
#     ".jobs.*.runs-on",
#     ".jobs.*.steps",

#     # obligatory inside step — at least one of 2
#     ".jobs.*.steps.*.run",
#     ".jobs.*.steps.*.uses",

#     # often optional — check if exists
#     ".jobs.*.needs",
#     ".jobs.*.if",
#     ".jobs.*.timeout-minutes",
#     ".jobs.*.env",
#     ".jobs.*.permissions",
#     ".jobs.*.strategy",
#     ".jobs.*.strategy.matrix",
#     ".jobs.*.continue-on-error",

#     # inside step
#     ".jobs.*.steps.*.name",
#     ".jobs.*.steps.*.with",
#     ".jobs.*.steps.*.env",
#     ".jobs.*.steps.*.if",
#     ".jobs.*.steps.*.continue-on-error",
#     ".jobs.*.steps.*.timeout-minutes",

#     # triggers
#     ".on.push.branches",
#     ".on.pull_request.branches",
#     ".on.workflow_dispatch",
#     ".on.workflow_call",
#     ".on.schedule",
# ]


# Need to extend as much as possible
DEPRECATED_ACTIONS: Final[list[str]] = [
    # actions/
    "actions/checkout@v1",
    "actions/checkout@v2",
    "actions/checkout@v3",
    "actions/setup-python@v1",
    "actions/setup-python@v2",
    "actions/setup-python@v3",
    "actions/setup-node@v1",
    "actions/setup-node@v2",
    "actions/setup-node@v3",
    "actions/setup-java@v1",
    "actions/setup-java@v2",
    "actions/cache@v1",
    "actions/cache@v2",
    "actions/upload-artifact@v1",
    "actions/upload-artifact@v2",
    "actions/upload-artifact@v3",
    "actions/download-artifact@v1",
    "actions/download-artifact@v2",
    "actions/download-artifact@v3",
    "actions/github-script@v1",
    "actions/github-script@v2",
    "actions/github-script@v3",
    "actions/github-script@v4",
    "actions/github-script@v5",
    # docker/
    "docker/login-action@v1",
    "docker/build-push-action@v1",
    "docker/build-push-action@v2",
    "docker/metadata-action@v1",
    "docker/metadata-action@v2",
    "docker/metadata-action@v3",
    # aws
    "aws-actions/configure-aws-credentials@v1",
    "aws-actions/configure-aws-credentials@v2",
    # google
    "google-github-actions/auth@v0",
    "google-github-actions/setup-gcloud@v0",
    # hashicorp
    "hashicorp/setup-terraform@v1",
    "hashicorp/setup-terraform@v2",
    # codecov
    "codecov/codecov-action@v1",
    "codecov/codecov-action@v2",
    # telegram
    "telegram-action@v1",
    "appleboy/telegram-action@v0.1.0",
    "appleboy/telegram-action@v0.1.1",
]


PROJECT_DESCRIPTION = """
    flowguard is a command-line tool for validating YAML configuration files and visualizing their structure.
    It combines yq-based checks, JSON Schema validation, and graph generation to make configuration quality
    gates CI-friendly and easier to debug.
    """
