# Exit codes

CodeGuard's exit code is a stable contract you can gate CI on.

| Code | Meaning |
|---|---|
| `0` | Completed; no findings (in v2.0: none at or above `--fail-on`, or `--exit-zero` was set). |
| `1` | Completed; one or more findings (in v2.0: at or above `--fail-on`). |
| `2` | Usage error — bad flag, unknown rule ID, unreadable path. |
| `3` | Config error — invalid `codeguard.toml` *(v2.0)*. |
| `4` | Internal error — an unexpected exception *(v2.0)*. |

Today codes `3` and `4` are folded into `2`. `0` and `1` are unchanged.

Suppressed findings never affect the exit code.
