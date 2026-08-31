# Configuration

!!! warning "Arrives in v2.0"
    Config-file support is not yet implemented. Today, configure a run with CLI flags
    (see [Usage](usage.md)). This page describes the planned v2.0 model.

## File

CodeGuard reads **`codeguard.toml`** from the project root, or a `[tool.codeguard]`
table in `pyproject.toml`. In a monorepo the nearest config to each scanned file wins,
merged with configs above it.

```toml
[tool.codeguard]
include    = ["src/**", "lib/**"]
exclude    = ["**/*.min.js", "tests/fixtures/**"]
languages  = ["python", "javascript", "typescript"]
fail_on    = "high"        # minimum severity that yields exit 1
gitignore  = true
baseline   = ".codeguard-baseline.json"

[tool.codeguard.rules]
disable = ["CG-SEC-002"]

[tool.codeguard.rules.CG-SEC-002]
severity = "medium"

[[tool.codeguard.overrides]]
path    = "migrations/**"
disable = ["CG-SEC-001"]
```

Validate it with `codeguard validate`. A JSON Schema is published for editor
autocompletion.
