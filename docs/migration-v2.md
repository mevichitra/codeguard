# Migrating to v2

v2.0 is a large step up from the 0.1 alpha. This page collects every
backward-incompatible change so an upgrade is predictable. It is filled in as each
change lands on `main`; see `changelog.d/` for the in-flight set.

## Already on `main`

### Package renamed: `codeguard` → `codeguard-cli`

The bare `codeguard` name on PyPI belongs to an unrelated project. Install
`codeguard-cli` instead (`pipx install codeguard-cli`). The **command**
(`codeguard`) and the **import package** (`import codeguard`) are unchanged. If
you pinned `codeguard` in a requirements file, switch it to `codeguard-cli`.

### `Location.col` is 1-indexed

Was 0-indexed. Adjust tooling that reads `col` from JSON output; SARIF column
values are unchanged in effect (the formatter no longer adds its own `+1`).

### `--format json` is an envelope object

`{ schema_version, tool, rules, results, summary }`. Parse `.results` instead of
the top-level array, or pass `--format json-legacy` (deprecated, one more minor
version) for the old bare array.

### `--fail-on` replaces `--severity` for gating

`--fail-on {severity|never}` controls the exit code (default `info`, so any
finding still fails by default). `--severity` is a deprecated alias.

### Exit codes 3 and 4

Config errors now exit `3`, unexpected internal errors exit `4`. `0`/`1`/`2` are
unchanged — only broaden handling if you special-cased `2`.

### `scan` respects `.gitignore` and skips vendor directories

Directory scans skip `.gitignore`d paths, `.venv` / `node_modules` /
`__pycache__` / `dist` / `build` / …, and generated files (`*.min.js`,
`*.d.ts`). Pass `--no-gitignore` to restore the old breadth; an explicitly named
file is always scanned.

### SARIF `partialFingerprints`

GitHub code scanning re-keys existing alerts once on upgrade, then stays stable.

### Rule authoring API (custom rules only)

`Rule.check(tree, source, filename)` → `Rule.analyze(ctx)`; a `languages`
attribute is required. Built-in Python rules subclass `AstRule` and keep
`check_ast(tree, source, filename)` unchanged.

## Planned (not yet on `main`)

| Change | What to do |
|---|---|
| Inline suppressions require `reason:` | Add `reason: …` to each `# codeguard: ignore[…]`. Bare ones still suppress but raise `CG-META-001`. |
| `disable[…]` → `ignore-file[…]` | Rename at leisure; the old spelling stays as a deprecated alias. |
