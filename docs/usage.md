# Usage

```bash
codeguard scan PATH
```

`PATH` is a file or a directory (scanned recursively for `*.py`).

## Options

| Flag | Description |
|---|---|
| `--format {human,json,sarif}` | Output format. Default `human`. |
| `--rule RULE_ID` | Only run the named rule(s). Repeatable. Validated against the registry. |
| `--severity {critical,high,medium,low,info}` | Only report findings at or above this level. |
| `--show-suppressed` | Include suppressed findings in the output. |
| `-o, --output PATH` | Write output to a file instead of stdout. |

## Examples

```bash
codeguard scan src/
codeguard scan auth.py --format json
codeguard scan src/ --format sarif -o results.sarif
codeguard scan . --rule CG-SEC-001 --rule CG-SEC-002
codeguard scan . --severity high
```

## Exit codes

`0` no findings · `1` findings · `2` error. Full contract in [Exit codes](exit-codes.md).

!!! note "Changing in v2.0"
    v2.0 adds `codeguard ci`, `baseline`, `list-rules`, `explain`, `validate`, and `init`
    commands, a [config file](configuration.md), `--fail-on` / `--diff` / `--baseline` /
    `--jobs` / `--exclude` flags, stdin input, and `.gitignore`-aware discovery. `--severity`
    becomes a display filter and `--fail-on` controls the exit code.
