# CI integration

## GitHub Actions (today)

```yaml
- name: Run CodeGuard
  run: |
    pip install codeguard-cli
    codeguard scan src/ --format sarif -o codeguard.sarif || true

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: codeguard.sarif
```

Findings then appear in the repository's **Security → Code scanning** tab and as
annotations on pull requests.

## v2.0

- **`codeguard ci`** — scans only files changed since the merge-base, applies a baseline,
  emits SARIF plus inline PR annotations.
- **`.pre-commit-hooks.yaml`** — `codeguard` (fast, changed files), `codeguard-full`
  (pre-push), `codeguard-ci` (manual).
- **`codeguard-action`** — a Marketplace action wrapping the above.
- **Docker image** — `ghcr.io/mevichitra/codeguard`.
- **Standalone binaries** — attached to each GitHub release.

See [Exit codes](exit-codes.md) for gating and [Configuration](configuration.md) for the
shared config file.
