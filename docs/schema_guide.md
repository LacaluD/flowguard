### How to write your own schema
Use [schema_examples/schema_example.json](schema_examples/schema_example.json), [schema_examples/schema_example.yml](schema_examples/schema_example.yml), and [schema_examples/schema_example_valid.yml](schema_examples/schema_example_valid.yml) as a baseline.

Rules:

- Start with `type: object` and an explicit `required` list for critical root fields (`name`, `on`, `jobs`, etc.).
- Lock structure with `additionalProperties: false` on root and nested objects where strict validation is needed.
- Reuse structure through `definitions` + `$ref` for repeated blocks (for example `job` and `step`).
- For fields with multiple accepted shapes, use `oneOf` (example: `runs-on` as string or array).
- Enforce practical constraints with `minItems`, `minLength`, `enum`, and `pattern` to catch real mistakes early.
- For YAML schemas and YAML configs, quote `"on"` as a key (`"on": ...`) to avoid YAML boolean coercion in PyYAML.

Anti-examples:

- Too permissive:
```yaml
type: object
additionalProperties: true
```

- Missing required keys (schema allows half-broken config):
```yaml
type: object
properties:
    jobs:
        type: object
```

- Ambiguous YAML key (parsed as boolean, not as field name):
```yaml
on:
    push:
        branches: [main]
```

Use this instead:
```yaml
"on":
    push:
        branches: [main]
```