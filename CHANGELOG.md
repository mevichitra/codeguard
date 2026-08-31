# Changelog

All notable changes to CodeGuard are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
CodeGuard follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). From
`2.0.0` the rule IDs, `Finding` / JSON schema, config keys, and CLI exit codes are a
stable contract.

Entries are assembled by [towncrier](https://towncrier.readthedocs.io/) from news
fragments in `changelog.d/` — run `towncrier build --draft` to preview unreleased
changes.

`2.0.0` is a large step from the `0.1` alpha (multi-language scanning, config file,
diff-aware CI, baselines, packaged distribution). See
[docs/migration-v2.md](docs/migration-v2.md) for every backward-incompatible change.

<!-- towncrier release notes start -->

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
