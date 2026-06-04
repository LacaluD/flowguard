### How to write your own schema

Use [schema_example.json](schema_example.json), [schema_example.yml](schema_example.yml), and [schema_example_valid.yml](schema_example_valid.yml) as a baseline.

### Core recommendations

Follow these rules to keep schemas strict, practical, and reliable:

1. Start from the root object:

```yaml
type: object
required: ["name", "on", "jobs"]
additionalProperties: false
```

2. Explicitly define `required` for all critical sections.

3. Close structures with `additionalProperties: false` where strict validation is needed:
- root
- job
- step
- with/env (if you want to reject unknown keys)

4. Reuse repeated blocks via `definitions` + `$ref`:
- job
- step
- action-like step

5. Use `oneOf` for fields with multiple valid shapes:
- `runs-on`: string or array of strings
- `needs`: string or array of strings

6. Add practical constraints:
- `minItems`
- `minLength`
- `enum`
- `pattern`
- `uniqueItems`

YAML-specific rule:
always quote the key `"on"` to avoid PyYAML boolean coercion.

Example:

```yaml
"on":
  push:
    branches: ["main"]
```

### Additional tips

1. Tighten schemas incrementally: start with critical fields, then add stricter checks.
2. A good schema not only catches errors but also guides consistent config authoring.
3. Use `pattern` for job names, step names, env keys, and other format-sensitive fields.
4. For real CI pipelines, strongly consider:
- `timeout-minutes >= 1`
- `minItems` for `steps`
- `uses` format check with pattern like `repo/action@version`
5. Keep schema, valid example YAML, and validation command together so CI/local checks stay simple.

### Anti-patterns to avoid

| Bad | Why it is bad | Better approach |
|---|---|---|
| `additionalProperties: true` | Too permissive, validates almost anything | `additionalProperties: false` in critical objects |
| Missing `required` | Broken configs pass validation | Explicitly list required keys |
| `on:` without quotes | May be interpreted as boolean | `"on":` |
| `oneOf` without constraints | Branches become too broad | Strict types and constraints in each branch |
| Overly broad `pattern` (for example `.*`) | Formally valid but low quality | Use target regex for specific field formats |

### Pre-commit checklist

1. `required` is defined for root and key nested sections.
2. No unnecessary permissive logic in `additionalProperties`.
3. Alternative field shapes are covered via `oneOf`.
4. At least one valid and one invalid example exist.
5. Local validation with `--schema` returns expected result.

### Repository demo pair

- YAML config: `demo/yml_demo_small_v2.yml`
- Custom schema: `demo/demo_small_schema.json`

Validate locally:

```bash
python main.py --files demo/yml_demo_small_v2.yml --schema demo/demo_small_schema.json
```