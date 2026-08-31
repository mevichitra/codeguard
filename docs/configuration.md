# Configuration

CodeGuard reads **`codeguard.toml`** (or `.codeguard.toml`) from your project,
falling back to a `[tool.codeguard]` table in `pyproject.toml`. Discovery walks
up from the working directory and stops at the repository root.

Generate a starter file:

```bash
codeguard init
```

Check a file:

```bash
codeguard validate
```

## Example

```toml
[codeguard]                       # in pyproject.toml this is [tool.codeguard]
include   = ["src/**", "lib/**"]  # empty = every supported file
exclude   = ["**/*.min.js", "tests/fixtures/**"]
languages = ["python"]
gitignore = true                  # honour .gitignore (default true)
fail_on   = "high"                # min severity that makes the run exit 1
output    = "human"               # default --format
jobs      = 0                     # 0 = one worker per CPU

[codeguard.rules]
disable = ["CG-SEC-002"]
enable  = []                      # empty = all (minus `disable`)

[codeguard.rules.CG-SEC-001]
severity       = "medium"         # remap this rule's severity
confidence_min = 0.8              # drop findings below this confidence

[codeguard.severity_remap]
CG-SEC-005 = "critical"

[[codeguard.overrides]]
path    = "migrations/**"         # gitignore-style glob, repo-relative
disable = ["CG-SEC-001"]          # or ["ALL"]
```

CLI flags win over the config file. `--config PATH` forces a specific file.

## Keys

| Key | Type | Default | Meaning |
|---|---|---|---|
| `include` / `exclude` | list of globs | `[]` | Gitignore-style path filters. |
| `languages` | list | all | Restrict to these languages. |
| `gitignore` | bool | `true` | Honour the repo `.gitignore`. |
| `fail_on` | severity or `"never"` | `"info"` | Exit-code threshold. |
| `output` | format | `"human"` | Default `--format`. |
| `jobs` | int | `0` | Worker processes (`0` = auto). |
| `baseline` | path | — | Baseline file *(used from a later release)*. |
| `[rules] disable` / `enable` | list of IDs | `[]` | Turn rules off / restrict to a set. |
| `[rules.<ID>] severity` | severity | — | Per-rule severity remap. |
| `[rules.<ID>] confidence_min` | float | — | Drop that rule's low-confidence findings. |
| `[severity_remap]` | table | `{}` | `RULE-ID = "severity"`. |
| `[[overrides]]` | array of tables | `[]` | `path` glob + `disable` / `enable`. |

!!! note "Monorepo nearest-wins"
    Per-directory config resolution (a nested `codeguard.toml` overriding the one
    above it, per scanned file) is planned. Today one effective config applies to
    the whole run; `[[overrides]]` with path globs covers most monorepo needs.
