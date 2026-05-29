"""Project-wide constants for YAML validation rules and default locations.

This module keeps static values in one place to avoid duplication and to make
future configuration extraction straightforward.
"""

from typing import Final

PROJECT_DESCRIPTION = """
    flowguard is a command-line tool for validating YAML configuration files and visualizing their structure.
    It combines yq-based checks, JSON Schema validation, and graph generation to make configuration quality
    gates CI-friendly and easier to debug.
    """

INDENT_SIZE: Final[int] = 2

YAML_ONLY_CHECKS: Final[list[str]] = [
    ".on",
]

EXTENDED_CHECKS: Final[list[str]] = [
    # obligatory
    ".name",
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


# Will be used later
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
    "actions/setup-java@v3",
    "actions/setup-go@v1",
    "actions/setup-go@v2",
    "actions/setup-go@v3",
    "actions/setup-dotnet@v1",
    "actions/setup-dotnet@v2",
    "actions/cache@v1",
    "actions/cache@v2",
    "actions/cache@v3",
    "actions/upload-artifact@v1",
    "actions/upload-artifact@v2",
    "actions/upload-artifact@v3",
    "actions/download-artifact@v1",
    "actions/download-artifact@v2",
    "actions/download-artifact@v3",
    "actions/download-artifact@v4",
    "actions/github-script@v1",
    "actions/github-script@v2",
    "actions/github-script@v3",
    "actions/github-script@v4",
    "actions/github-script@v5",
    "actions/stale@v1",
    "actions/stale@v2",
    "actions/stale@v3",
    "actions/stale@v4",
    "actions/labeler@v1",
    "actions/labeler@v2",
    "actions/labeler@v3",
    "actions/first-interaction@v1",
    "actions/create-release@v1",
    "actions/upload-release-asset@v1",
    # docker/
    "docker/login-action@v1",
    "docker/login-action@v2",
    "docker/build-push-action@v1",
    "docker/build-push-action@v2",
    "docker/build-push-action@v3",
    "docker/metadata-action@v1",
    "docker/metadata-action@v2",
    "docker/metadata-action@v3",
    "docker/setup-buildx-action@v1",
    "docker/setup-buildx-action@v2",
    "docker/setup-qemu-action@v1",
    "docker/setup-qemu-action@v2",
    # aws
    "aws-actions/configure-aws-credentials@v1",
    "aws-actions/configure-aws-credentials@v2",
    "aws-actions/configure-aws-credentials@v3",
    "aws-actions/amazon-ecr-login@v1",
    "aws-actions/amazon-ecs-deploy-task-definition@v1",
    # google
    "google-github-actions/auth@v0",
    "google-github-actions/auth@v1",
    "google-github-actions/setup-gcloud@v0",
    "google-github-actions/setup-gcloud@v1",
    "google-github-actions/deploy-cloudrun@v0",
    "google-github-actions/deploy-cloudrun@v1",
    # hashicorp
    "hashicorp/setup-terraform@v1",
    "hashicorp/setup-terraform@v2",
    # codecov
    "codecov/codecov-action@v1",
    "codecov/codecov-action@v2",
    "codecov/codecov-action@v3",
    # github
    "github/codeql-action/init@v1",
    "github/codeql-action/analyze@v1",
    "github/codeql-action/autobuild@v1",
    "github/super-linter@v3",
    "github/super-linter@v4",
    # sonarsource
    "sonarsource/sonarcloud-github-action@v1",
    "sonarsource/sonarcloud-github-action@v2",
    # jetbrains
    "JetBrains/qodana-action@v2021",
    "JetBrains/qodana-action@v2022",
    "JetBrains/qodana-action@v2023",
    # telegram
    "telegram-action@v1",
    "appleboy/telegram-action@v0.1.0",
    "appleboy/telegram-action@v0.1.1",
    "cbrgm/telegram-github-action@v1",
    # slack
    "slackapi/slack-github-action@v1.1.0",
    "slackapi/slack-github-action@v1.2.0",
    "slackapi/slack-github-action@v1.3.0",
    "slackapi/slack-github-action@v1.4.0",
    "slackapi/slack-github-action@v1.5.0",
    "slackapi/slack-github-action@v1.6.0",
    "8398a7/action-slack@v2",
    "8398a7/action-slack@v3",
    # peter-evans
    "peter-evans/create-pull-request@v3",
    "peter-evans/create-pull-request@v4",
    "peter-evans/find-comment@v1",
    "peter-evans/find-comment@v2",
    "peter-evans/create-or-update-comment@v1",
    "peter-evans/create-or-update-comment@v2",
    # softprops
    "softprops/action-gh-release@v1",
    # EndBug
    "EndBug/add-and-commit@v7",
    "EndBug/add-and-commit@v8",
    # stefanzweifel
    "stefanzweifel/git-auto-commit-action@v4",
]
