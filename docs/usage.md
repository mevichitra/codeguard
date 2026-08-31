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
| `ci` | Diff-aware scan for pull requests — see [CI integration](ci.md). |
| `baseline create / update / prune` | Manage a [baseline](baseline.md) file. |
| `list-rules` | List every registered rule (`--format json`, `--language`, `--category`, `--severity`). |
| `explain <RULE_ID>` | Full description, CWE/OWASP, and docs link for a rule. |
| `validate` | Validate `codeguard.toml`. |
| `init` | Write a starter `codeguard.toml`. |

## `scan` / `ci` options

| Flag | Description |
|---|---|
| `--config PATH` | Use a specific config file. |
| `--format {human,json,json-legacy,sarif,github,rdjson,junit}` | Output format. See [Output formats](output-formats.md). |
| `--rule RULE_ID` | Only run the named rule(s). Repeatable. |
| `--exclude GLOB` / `--include GLOB` | Path filters. Repeatable. |
| `--diff REF` | Only scan files changed since `REF` (merge-base with `HEAD`). |
| `--baseline PATH` | Findings in the baseline don't fail the run. |
| `--fail-on {critical,high,medium,low,info,never}` | Minimum severity that makes the run exit `1` (default `info`). |
| `--exit-zero` | Always exit `0` (report-only). |
| `--no-gitignore` | Do not read `.gitignore`. |
| `-j, --jobs N` | Parallel worker processes (`0` = one per CPU). |
| `--show-suppressed` | Include suppressed / baselined findings in the output. |
| `-q, --quiet` | Only print findings. |
| `--no-color` | Disable colour (also honours `NO_COLOR`). |
| `-o, --output PATH` | Write output to a file. |
| `--severity LEVEL` | **Deprecated** alias of `--fail-on`. |

`ci` additionally takes `--sarif PATH` (write a SARIF report as well) and, when
`--diff` is omitted, auto-detects the base branch.

## Examples

```bash
codeguard scan src/
codeguard scan . --fail-on high --format sarif -o results.sarif
codeguard scan . --exclude "migrations/**" -j 0
codeguard scan . --diff origin/main --baseline .codeguard-baseline.json
codeguard ci --diff origin/main --sarif codeguard.sarif
codeguard explain CG-SEC-001
```

See [Exit codes](exit-codes.md) and [Configuration](configuration.md).
