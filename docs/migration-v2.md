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

### Multi-language: JavaScript and TypeScript

CodeGuard now scans `.js` / `.jsx` / `.mjs` / `.cjs` and `.ts` / `.tsx` / `.mts` /
`.cts` (tree-sitter). Six rules ship in the `CG-SEC-1xx` block. `pip install
codeguard-cli` pulls the tree-sitter grammar packages automatically; nothing to
configure.

### Rule authoring API (custom rules only)

`Rule.check(tree, source, filename)` → `Rule.analyze(ctx)`; a `languages`
attribute is required. Python rules subclass `AstRule` and keep
`check_ast(tree, source, filename)`; JavaScript / TypeScript rules subclass
`TreeSitterRule` and implement `check_tree(root, ctx)` over a `SourceNode`.

### Suppressions require a reason; `disable` renamed

Add `reason: …` to every `# codeguard: ignore[…]` — bare ones still suppress but
raise the new low-severity `CG-META-001`. `# codeguard: disable[…]` is now a
deprecated spelling of `# codeguard: ignore-file[…]` (still works). An
`until=YYYY-MM-DD` that has passed reactivates the finding and raises
`CG-META-002`. Audit with `codeguard suppressions list`.

### Test fixtures moved (contributors)

`tests/fixtures/<category>/<rule_id>/` → `tests/fixtures/<language>/<category>/<rule_id>/`,
and `conftest.load_fixture` gained a leading `language` argument.

## Planned (not yet on `main`)

Nothing outstanding — v2.0 is feature-complete pending release packaging.
