# Usage

```bash
codeguard scan [PATHS]...
```

`PATHS` are files or directories (default `.`). Directories are scanned
recursively, honouring `.gitignore` and skipping vendor/build directories. Read
from stdin with `-`.

## Commands

| Command | Purpose |
|---|---|
| `scan` | Scan paths and report findings. |
| `list-rules` | List every registered rule (`--format json`, `--language`, `--category`, `--severity`). |
| `explain <RULE_ID>` | Full description, CWE/OWASP, and docs link for a rule. |
| `validate` | Validate `codeguard.toml`. |
| `init` | Write a starter `codeguard.toml`. |

## `scan` options

| Flag | Description |
|---|---|
| `--config PATH` | Use a specific config file. |
| `--format {human,json,json-legacy,sarif}` | Output format. `json-legacy` is the deprecated bare array. |
| `--rule RULE_ID` | Only run the named rule(s). Repeatable. |
| `--exclude GLOB` / `--include GLOB` | Path filters. Repeatable. |
| `--fail-on {critical,high,medium,low,info,never}` | Minimum severity that makes the run exit `1` (default `info`). |
| `--exit-zero` | Always exit `0` (report-only). |
| `--no-gitignore` | Do not read `.gitignore`. |
| `-j, --jobs N` | Parallel worker processes (`0` = one per CPU). |
| `--show-suppressed` | Include suppressed findings in the output. |
| `-q, --quiet` | Only print findings. |
| `--no-color` | Disable colour (also honours `NO_COLOR`). |
| `--stdin-filename NAME` | Filename to assume for `-`. |
| `-o, --output PATH` | Write output to a file. |
| `--severity LEVEL` | **Deprecated** alias of `--fail-on`. |

## Examples

```bash
codeguard scan src/
codeguard scan . --fail-on high --format sarif -o results.sarif
codeguard scan . --exclude "migrations/**" -j 0
git diff --name-only --diff-filter=d | xargs codeguard scan
codeguard explain CG-SEC-001
```

See [Exit codes](exit-codes.md) and [Configuration](configuration.md).
