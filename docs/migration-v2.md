# Migrating to v2

v2.0 is a large step up from the 0.1 alpha. This page collects every
backward-incompatible change so an upgrade is predictable. It is filled in as each
change lands on `main`; see `changelog.d/` for the in-flight set.

## Already on `main`

### Package renamed: `codeguard` → `codeguard-cli`

The bare `codeguard` name on PyPI belongs to an unrelated project. Install
`codeguard-cli` instead:

```bash
pipx install codeguard-cli      # was: pipx install codeguard
```

The **command** (`codeguard`) and the **import package** (`import codeguard`) are
unchanged. If you pinned `codeguard` in a requirements file, switch it to
`codeguard-cli`.

## Planned (not yet on `main`)

| Change | What to do |
|---|---|
| Rule API `check(tree, …)` → `analyze(ctx)`; `languages` attribute required | Only affects custom rules. Built-in rules are cushioned by an `AstRule` base. |
| `Location.col` becomes 1-indexed (was 0-indexed) | Adjust any tooling that reads `col` from JSON output. SARIF column values are unaffected. |
| `--format json` becomes an envelope object | Parse `.results` instead of the top-level array, or use `--format json-legacy` for one more minor version. |
| `scan --severity` splits into `--fail-on` (exit code) + display filter | Use `--fail-on` in CI gates. `--severity` keeps working as a deprecated alias. |
| Exit codes `3` (config) and `4` (internal) added | `0` and `1` are unchanged; only broaden handling if you special-cased `2`. |
| Inline suppressions require `reason:` | Add `reason: …` to each `# codeguard: ignore[…]`. Bare ones still suppress but raise `CG-META-001`. |
| `disable[…]` → `ignore-file[…]` | Rename at leisure; the old spelling stays as a deprecated alias. |
| `scan` respects `.gitignore` + a built-in skip list by default | Pass `--no-gitignore` to restore the previous breadth. |
| SARIF `partialFingerprints` added | GitHub code scanning re-keys existing alerts once on upgrade, then stays stable. |
