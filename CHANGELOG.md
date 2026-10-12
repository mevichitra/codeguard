# Changelog

All notable changes to CodeGuard are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
CodeGuard follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). From
`2.0.0` the rule IDs, `Finding` / JSON schema, config keys, and CLI exit codes are a
stable contract.

Entries are assembled by [towncrier](https://towncrier.readthedocs.io/) from news
fragments in `changelog.d/` — run `towncrier build --draft` to preview unreleased
changes. See [docs/releasing.md](docs/releasing.md) for how a release is cut.

The editor extensions are versioned separately and keep their own changelogs:
[VS Code](editors/vscode/CHANGELOG.md) and [Zed](editors/zed/CHANGELOG.md).

`2.0.0` is a large step from the `0.1` alpha (multi-language scanning, config file,
diff-aware CI, baselines, packaged distribution). See
[docs/migration-v2.md](docs/migration-v2.md) for every backward-incompatible change.

<!-- --8<-- [start:releases] -->
<!-- towncrier release notes start -->

## [2.2.0] - 2026-10-12

### Added

- Added 28 rules. Security: weak hashes for passwords and tokens (CG-SEC-006, CG-SEC-107), disabled TLS verification (CG-SEC-007, CG-SEC-108), `tempfile.mktemp` (CG-SEC-008), the `random` module for secrets (CG-SEC-009, with autofix), and Express open redirects, path traversal, and prototype pollution (CG-SEC-109 to CG-SEC-111). Performance: CG-PERF-001 to 005 for Python and CG-PERF-101 to 105 for JavaScript and TypeScript. Code quality: CG-QUAL-001 to 005 for Python and CG-QUAL-101 to 104 for JavaScript and TypeScript, with configurable complexity, nesting, and parameter limits.
- Added intraprocedural taint tracking for Python and five rules built on it: untrusted input reaching a SQL query (CG-SEC-010), a shell command (CG-SEC-011), `eval`/`exec` (CG-SEC-012), a file path (CG-SEC-013), or a redirect (CG-SEC-014). Each finding lists the source and every assignment on the way, in the terminal, SARIF, and the editor; on the same line it replaces the matching pattern rule finding.
- Findings can now carry a safe autofix and related locations, both emitted in JSON (`fix`, `related`) and SARIF (`fixes`, `relatedLocations`). Rules can declare tunable options set under `[rules.<ID>]` in `codeguard.toml`, and the `languages` config key now restricts discovery. The JSON summary gained `by_category` and `fixable` counts.
- New `categories` config key. `scan` and `ci` run security rules by default, so upgrading does not change any exit code; enable performance and quality rules with `categories = [...]` or `--category`. Rules named with `--rule` or `[rules] enable` always run.
- The language server now maps finding severity to editor severity (critical/high as errors, medium as warnings, low as information, info as hints; configurable with `severityMap`), offers quick fixes, line- and file-level suppressions, an Explain action, and a `source.fixAll.codeguard` action, shows hovers with the taint data-flow path, reports workspace-scan progress, and answers the custom `codeguard/summary` and `codeguard/fixAll` requests (with a `codeguard/summaryChanged` notification) that editor panels build on. Editors show security, performance, and quality findings by default; `categories` and `rules.disable` settings tune this. Results are cached per document, configuration is reloaded only when it changes, and positions are converted to UTF-16 so ranges and fixes are exact on lines with non-ASCII text.
- VS Code extension 0.2.0: a CodeGuard activity-bar view that groups findings by severity, category, or file with inline fix and explain actions; live status-bar counts; a Security Overview panel; fix-all commands for a file or the whole workspace; SARIF export; settings for categories, severity mapping, and editor-only rule disabling; and a getting-started walkthrough. The extension now declares VS Code 1.82 as its minimum, which its language client already required.
- Zed extension 0.2.0: settings under `lsp.codeguard` (`initialization_options` and `settings`) reach the server, so severity mapping, categories, and editor-only rule disabling work in Zed; `lsp.codeguard.binary` can point at a specific executable; Windows virtual environments are found; and the manifest declares CodeGuard's quick-fix and fix-all code-action kinds so `code_actions_on_format` can run them.
- `codeguard scan --fix` applies safe autofixes in place and reports the post-fix state; `--fix-dry-run` prints them as a unified diff. `scan` and `ci` accept `--category` to run only security, performance, or quality rules. `list-rules` shows a fix column and gains `--fixable`; `explain` shows autofix support and rule options; `validate` rejects unknown rule options. The `output` config key now accepts every `--format` value.

### Fixed

- CG-SEC-001 now catches a query built with string formatting in a variable and executed on a later line, and no longer flags concatenation with a local variable that holds a string constant.
- Language-server commands moved to the `codeguard.lsp.*` namespace so they no longer collide with the VS Code extension's own commands; `codeguard.openDashboard` is still accepted.
- Rule documentation links in SARIF, JSON, `explain`, and editor diagnostics now use the published page path (`rules/CG-SEC-001/`); the previous lowercase links returned 404.
- `import random as rnd` no longer makes the unbound name `random` resolve as the module when matching calls.

### Documentation

- Added guides for taint tracking, autofix, and editor integration (VS Code, Zed, Neovim, Helix, and the custom LSP protocol), a roadmap, rule pages for every rule grouped by category, an updated contributor guide, and `scripts/scaffold_rule_docs.py` to start a new rule's page from its metadata and fixtures. The README describes 2.2 accurately.
- Added rule pages for CG-SEC-101 to CG-SEC-106 and the CG-META rules, and corrected stale statements about config discovery and baselines.
- The changelog now has a page on the documentation site, the release process is written down in `docs/releasing.md`, and the VS Code and Zed extensions keep their own changelogs.

### Internal

- A new Editors workflow compiles, unit-tests, and packages the VS Code extension and lints, tests, and builds the Zed extension for `wasm32-wasip2` on every change under `editors/` or `src/codeguard/lsp/`.
- News fragments can now use the `changed`, `deprecated`, `removed`, and `security` types, so release notes follow Keep a Changelog sections. CI also requires an extension changelog entry when a PR changes an editor extension, and only a PR that adds a new release section to `CHANGELOG.md` is exempt from the fragment check.

## [2.1.0] - 2026-09-02

### Added

- Added a local Language Server Protocol command and a Zed development extension with workspace
  scanning, live warning diagnostics, and a local Markdown security dashboard for Python,
  JavaScript, JSX, TypeScript, and TSX.

## [2.0.0] - 2026-08-31

### Breaking changes

- Exit codes `3` (config error) and `4` (internal error) are now distinct from `2` (usage error); `0` and `1` are unchanged. The `scan --severity` flag is a deprecated alias of the new `--fail-on` (which controls the exit code); `--fail-on` defaults to `info`.
- The PyPI project is now `codeguard-cli` (the bare `codeguard` name belongs to an unrelated project). The installed command and the import package are both still `codeguard`. Install with `pipx install codeguard-cli` / `uv tool install codeguard-cli` / `pip install codeguard-cli`.
- The rule API changed: `Rule.check(tree, source, filename)` is now `Rule.analyze(ctx)`, taking a `RuleContext`, and every rule declares a `languages` set. Python rules that subclass the new `AstRule` keep their `check_ast(tree, source, filename)` method unchanged. A new `codeguard.lang` package provides the language adapter layer for the tree-sitter backends.
- `--format json` now emits an envelope object — `{ schema_version, tool, rules, results, summary }` — with a per-finding `fingerprint`. The previous bare-array output is available as `--format json-legacy` for one minor version and prints a deprecation warning.
- `Location.col` (and `end_col`) is now 1-indexed to match editors and SARIF. JSON `location.col` values shift by one; SARIF column values are unchanged in effect (the formatter no longer adds its own offset).

### Added

- Added `codeguard.toml` / `pyproject.toml [tool.codeguard]` configuration: `include`/`exclude`, `fail_on`, `output`, `jobs`, `gitignore`, `[rules] enable`/`disable`, per-rule `severity`/`confidence_min`, `[severity_remap]`, and path-scoped `[[overrides]]`. Config is discovered by walking up to the repository root; `codeguard validate` checks it and a starter file comes from `codeguard init`. ([#7](https://github.com/mevichitra/codeguard/issues/7))
- Suppression comments gained governance: a `reason:` is expected (bare ones raise `CG-META-001`), an `until=YYYY-MM-DD` reactivates the finding once past (`CG-META-002`), the file-level keyword is now `ignore-file[...]` (`disable[...]` is a deprecated alias), and `codeguard suppressions list [--expired] [--unused]` audits every suppression with an active/expired/unused status. `//` comments work for JavaScript and TypeScript. ([#9](https://github.com/mevichitra/codeguard/issues/9))
- Added a `.pre-commit-hooks.yaml` (hook ids `codeguard`, `codeguard-full`, `codeguard-ci`) and a composite GitHub Action at `action/` — `uses: mevichitra/codeguard/action@v2` — that runs `codeguard ci` and uploads SARIF to code scanning. ([#13](https://github.com/mevichitra/codeguard/issues/13))
- Added six JavaScript / TypeScript security rules (the `CG-SEC-1xx` block): dynamic code execution via `eval` / `new Function` / string timers (CG-SEC-101), `child_process.exec` shell injection (CG-SEC-102), DOM XSS sinks like `innerHTML` and `document.write` (CG-SEC-103), React `dangerouslySetInnerHTML` (CG-SEC-104), hardcoded secrets (CG-SEC-105), and `Math.random()` used for tokens or secrets (CG-SEC-106). ([#14](https://github.com/mevichitra/codeguard/issues/14))
- Added the tree-sitter language backends for JavaScript (`.js/.jsx/.mjs/.cjs`) and TypeScript (`.ts/.tsx/.mts/.cts`). `SourceNode` now wraps tree-sitter nodes as well as Python `ast` nodes, with `child_by_field` for named children. Grammars load lazily, so a Python-only scan never imports tree-sitter.
- Directory scans now honour the repository `.gitignore`, skip vendor/tooling directories (`.venv`, `node_modules`, `__pycache__`, `dist`, ...) and generated files (`*.min.js`, `*.d.ts`) by default, and never follow directory symlinks. `AnalysisRunner.run_files(..., jobs=N)` fans a scan across a process pool with output identical to a sequential run.
- Every finding now carries a stable `fingerprint` (scheme `codeguard/v1`) derived from the rule, the file, the enclosing function/class, and the normalized statement — stable across reformatting and line moves. SARIF output emits it as `partialFingerprints`, and it is the identity key for the baseline and diff workflows.
- New `codeguard ci` command: diff-aware scanning for pull requests. It scans only files changed since the base branch (auto-detected, or `--diff REF`), applies the baseline, defaults to GitHub Actions annotations, and can also write a SARIF report with `--sarif PATH`.
- New baseline support: `codeguard baseline create / update / prune` writes a fingerprint file of today's findings, and `scan --baseline PATH` (or `baseline = "..."` in config) marks those findings so they no longer fail the run. Baselined findings are hidden by default, revealed with `--show-suppressed`.
- New commands: `codeguard list-rules`, `codeguard explain <RULE-ID>`, `codeguard validate`, and `codeguard init`.
- SARIF output gained `partialFingerprints`, `security-severity`, `helpUri`, and CWE taxonomy tags on each rule.
- Three new `--format` options: `github` (GitHub Actions annotations), `rdjson` (reviewdog), and `junit` (JUnit XML).
- `codeguard scan --diff REF` restricts a scan to files changed since REF (merge-base with HEAD), including uncommitted and untracked changes.
- `codeguard scan` accepts multiple paths, reads stdin with `-`, and gains `--config`, `--exclude`/`--include`, `--fail-on`/`--exit-zero`, `--no-gitignore`, `-j/--jobs`, `-q/--quiet`, and `--no-color`.

### Fixed

- CG-SEC-005 now flags `os.system`, `os.popen`, `subprocess.getoutput`, and `subprocess.getstatusoutput` with a non-literal argument -- these always use a shell and have no `shell=` keyword, so they were previously missed entirely. ([#3](https://github.com/mevichitra/codeguard/issues/3))
- CG-SEC-004 and CG-SEC-005 now resolve import aliases, so `from pickle import loads`, `import subprocess as sp`, and `from os import system as sh` are detected. A shared resolver (`codeguard.rules._pyimports`) handles this. ([#4](https://github.com/mevichitra/codeguard/issues/4))
- CG-SEC-001 no longer reports a false positive for a multi-part concatenation of string literals such as `"SELECT " + " * " + " FROM t"`; the whole `+` tree is checked, not just the outermost operands. ([#5](https://github.com/mevichitra/codeguard/issues/5))
- Added the missing `.license-header.txt` so the `insert-license` pre-commit hook passes on a clean checkout.
- Fixed all in-repo GitHub URLs, which pointed at a non-existent `codeguard-ai/codeguard` org, to `mevichitra/codeguard` (including the SARIF `informationUri`).

### Documentation

- Added a documentation site (`docs/`, MkDocs + Material) covering install, usage, exit codes, suppressions, output formats, CI, architecture, and a v2 migration guide; published to GitHub Pages on release.
- Corrected the CWE reference for CG-SEC-003 in the README (CWE-95, matching the rule).
- Filled in the "Migrating to v2" guide with the changes that have landed (package rename, 1-indexed columns, JSON envelope, `--fail-on`, exit codes 3/4, gitignore-aware discovery, rule API).
- Rewrote the "Adding a rule" guide for the new `AstRule` / `analyze(ctx)` API and the import-alias resolver.

### Internal

- Added `TreeSitterRule`, a base class for JS/TS rules that walk a `SourceNode` tree, and `codeguard.rules._jsnodes` with call / argument / literal helpers. `run_benchmark.py` now also picks up `.js` / `.jsx` / `.ts` / `.tsx` corpus samples.
- Changelog is now assembled by towncrier from fragments in `changelog.d/`.
- Moved the abandoned FastAPI backend and the two React frontends (which shared no code with the CLI) into `archive/`; they are no longer built, tested, or released.
- Overhauled CI: concurrency cancellation, pip caching, a Windows/macOS/Python 3.13 test matrix, a build-and-install smoke test, `pip-audit`, a docs build, an old-org URL guard, and a changelog-fragment check. The release workflow now runs lint, types, and tests behind a tag/version consistency check before publishing.
- Seeded `benchmarks/corpus/` with true/false-positive cases for CG-SEC-001, CG-SEC-004, and CG-SEC-005 (precision and recall 1.0 on the seed set).
- Switched the build backend from setuptools to hatchling; the version is single-sourced from `src/codeguard/__init__.py`.
- Test fixtures moved to `tests/fixtures/<language>/<category>/<rule_id>/` and `conftest.load_fixture` gained a leading `language` argument, so JavaScript and TypeScript rules can carry their own fixtures.
- `scan` and `ci` share a single implementation (`codeguard.cli._run`); the `Finding` model gains a `baselined` flag.


## [0.1.0]

Initial alpha: AST rule engine, CLI (`scan`), and five security rules
(CG-SEC-001..005) with human / JSON / SARIF output and inline suppression comments.

[0.1.0]: https://github.com/mevichitra/codeguard/releases/tag/v0.1.0

<!-- --8<-- [end:releases] -->
