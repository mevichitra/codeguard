# CodeGuard GitHub Action

Diff-aware security scan for pull requests. Findings land on the PR as inline
annotations and (by default) in the repository's **Security → Code scanning** tab.

```yaml
name: CodeGuard
on:
  pull_request:
permissions:
  contents: read
  security-events: write   # for the SARIF upload
jobs:
  codeguard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0     # `ci` needs history to diff against the base branch
      - uses: mevichitra/codeguard/action@v2
        with:
          fail-on: high
```

## Inputs

| Input | Default | Description |
|---|---|---|
| `path` | `.` | Path to scan. |
| `config` | — | Path to `codeguard.toml`. |
| `fail-on` | — | Min severity that fails the check. |
| `baseline` | — | Baseline file; findings in it do not fail the check. |
| `diff` | auto | Base ref to diff against. |
| `sarif-file` | `codeguard.sarif` | Where the SARIF report is written. |
| `upload-sarif` | `true` | Upload SARIF to GitHub code scanning. |
| `version` | latest | `codeguard-cli` version to install. |
| `args` | — | Extra arguments for `codeguard ci`. |

The check fails (non-zero) exactly when `codeguard ci` does — new findings at or
above `fail-on`, ignoring anything in the baseline.
