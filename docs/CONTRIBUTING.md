## Repository contents

### Root files

| File | Purpose |
|---|---|
| [../main.py](../main.py) | CLI entry point that parses arguments, discovers binaries, and dispatches the validation or visualization pipeline. |
| [../version.py](../version.py) | Build metadata used for startup logging and release info. |
| [../pyproject.toml](../pyproject.toml) | Project metadata, dependency declarations, and tooling configuration. |
| [../requirements.in](../requirements.in) | High-level dependency list for the runtime environment. |
| [../requirements.txt](../requirements.txt) | Pinned dependency set used for reproducible installs. |
| [../LICENSE](../LICENSE) | MIT license text for the project. |
| [../README.md](../README.md) | Main project documentation and usage guide. |
| [../TODO.md](../TODO.md) | Roadmap, priorities, and planned follow-up work. |
| [../_test.py](../_test.py) | Local helper script kept in the root for quick manual experiments. |

### docs/

| File | Purpose |
|---|---|
| [schema_guide.md](schema_guide.md) | Guide for writing and applying custom JSON Schema files. |
| [bandit-report.txt](bandit-report.txt) | Bandit security scan output. |
| [coverage-report.txt](coverage-report.txt) | Coverage summary captured in CI or local runs. |
| [mypy-report.txt](mypy-report.txt) | mypy type-check report. |
| [safety-report.txt](safety-report.txt) | Safety dependency audit output. |
| [assets/demo.gif](assets/demo.gif) | Demo animation used on the project page. |

### demo/

| File | Purpose |
|---|---|
| [../demo/demo_small.yml](../demo/demo_small.yml) | Small YAML sample used for basic validation demos. |
| [../demo/demo_small_v2.yml](../demo/demo_small_v2.yml) | Second sample workflow used for comparisons and diff visualization. |
| [../demo/demo_small_schema.json](../demo/demo_small_schema.json) | Schema example paired with the demo workflows. |
| [../demo/demo_small.png](../demo/demo_small.png) | Rendered graph for the base demo config. |
| [../demo/demo_small_v2.png](../demo/demo_small_v2.png) | Rendered graph for the second demo config. |
| [../demo/demo_small.diff.svg](../demo/demo_small.diff.svg) | Config diff visualization for the demo pair. |
| [../demo/demo_small_v2.diff.png](../demo/demo_small_v2.diff.png) | Rendered diff output for the second demo file. |
| [../demo/demo_small_v2.job-deploy.diff.png](../demo/demo_small_v2.job-deploy.diff.png) | Job-scoped diff output for the `deploy` job. |

### configs/

| File | Purpose |
|---|---|
| [../configs/pytest.ini](../configs/pytest.ini) | pytest configuration and test discovery settings. |
| [../configs/mypy.ini](../configs/mypy.ini) | mypy configuration used for static type checking. |
| [../configs/bandit.yml](../configs/bandit.yml) | Bandit security scan configuration. |
| [../configs/coverage.json](../configs/coverage.json) | Coverage data artifact used by the pipeline. |

### schema_docs/

| File | Purpose |
|---|---|
| [../schema_docs/schema_guide.md](../schema_docs/schema_guide.md) | Reference guide for authoring and validating custom schemas. |
| [../schema_docs/schema_example.json](../schema_docs/schema_example.json) | Example JSON Schema definition used as a starting point. |
| [../schema_docs/schema_example.yml](../schema_docs/schema_example.yml) | Example YAML schema representation mirroring the JSON example. |
| [../schema_docs/schema_example_valid.yml](../schema_docs/schema_example_valid.yml) | Valid YAML config that satisfies the example schema. |
| [../schema_docs/schema_example_valid.png](../schema_docs/schema_example_valid.png) | Rendered visualization for the valid schema example config. |

### .github/workflows/

| File | Purpose |
|---|---|
| [../.github/workflows/main.yml](../.github/workflows/main.yml) | Main GitHub Actions workflow used to run checks and automation for the repository. |
| [../.github/workflows/main.svg](../.github/workflows/main.svg) | Rendered graph snapshot for the workflow definition. |
| [../.github/workflows/main.png](../.github/workflows/main.png) | PNG rendering of the workflow graph for documentation or inspection. |