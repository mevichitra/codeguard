# CI integration

## GitHub Action (recommended)

```yaml
name: CodeGuard
on:
  pull_request:
permissions:
  contents: read
  security-events: write
jobs:
  codeguard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # `ci` diffs against the base branch
      - uses: mevichitra/codeguard/action@v2
        with:
          fail-on: high
```

Findings appear as inline PR annotations and in **Security → Code scanning**.
See [`action/README.md`](https://github.com/mevichitra/codeguard/tree/main/action).

## `codeguard ci`

The action wraps this command; run it anywhere:

```bash
codeguard ci --diff origin/main --sarif codeguard.sarif
```

`ci` scans only files changed since the base branch (auto-detected, or `--diff REF`),
applies the [baseline](baseline.md), defaults to GitHub Actions annotations, and
uses the same [exit-code contract](exit-codes.md) as `scan`.

## Any CI, plain SARIF

```yaml
- run: pip install codeguard-cli
- run: codeguard scan src/ --format sarif -o codeguard.sarif || true
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: codeguard.sarif
```

## pre-commit

```yaml
repos:
  - repo: https://github.com/mevichitra/codeguard
    rev: v2.0.0
    hooks:
      - id: codeguard            # staged files, on every commit
      - id: codeguard-full       # whole tree, on push
        stages: [pre-push]
```

## GitLab / other

`--format rdjson` feeds [reviewdog](https://github.com/reviewdog/reviewdog) for
inline comments; `--format junit` feeds any JUnit-aware dashboard.
