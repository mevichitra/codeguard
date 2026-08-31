# Exit codes

CodeGuard's exit code is a stable contract you can gate CI on.

| Code | Meaning |
|---|---|
| `0` | Completed; no findings at or above `--fail-on` (or `--exit-zero` was set). |
| `1` | Completed; one or more findings at or above `--fail-on`. |
| `2` | Usage error — bad flag, unknown rule ID, missing path. |
| `3` | Config error — invalid `codeguard.toml`. |
| `4` | Internal error — an unexpected exception. |

`--fail-on` defaults to `info`, so by default any finding yields `1`. Use
`--fail-on high` to gate only on high/critical, or `--exit-zero` for a
report-only run.

Suppressed and baselined findings never affect the exit code.
