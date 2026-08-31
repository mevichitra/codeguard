# Changelog

All notable changes to CodeGuard are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
CodeGuard follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html); until
`2.0.0` the public interfaces (rule IDs, `Finding` schema, CLI flags) are not stable.

## [Unreleased]

Work toward **v2.0** — a production-ready, multi-language (Python + JavaScript +
TypeScript) SAST CLI. See `docs/` and the milestone plan for the full scope.

### Changed

- **Packaging:** the PyPI project is now **`codeguard-cli`** (the bare `codeguard`
  name belongs to an unrelated project). The installed command is still `codeguard`
  and the import package is still `codeguard`. Install with
  `pip install codeguard-cli` / `pipx install codeguard-cli` / `uv tool install codeguard-cli`.
- Build backend moved from setuptools to **hatchling**; the version is single-sourced
  from `src/codeguard/__init__.py`.

### Fixed

- All in-repo GitHub URLs pointed at a non-existent `codeguard-ai/codeguard` org;
  they now point at `mevichitra/codeguard` (including the SARIF `informationUri`).
- The `insert-license` pre-commit hook referenced a missing `.license-header.txt`;
  the file now exists so a clean checkout passes `pre-commit run --all-files`.

### Internal

- The abandoned FastAPI backend and the two React frontends (which shared no code
  with the CLI) moved to `archive/` and are excluded from tooling. They are not
  built, tested, or released.

### Planned breaking changes for 2.0

These are not yet in `main`; they are tracked here so the migration guide can be
written incrementally.

1. Rule authoring API: `Rule.check(tree, source, filename)` → `Rule.analyze(ctx)`;
   a `languages` attribute becomes required (`AstRule` cushions the built-ins).
2. `Location.col` becomes 1-indexed (was 0-indexed).
3. `--format json` emits an envelope object instead of a bare array
   (`--format json-legacy` retained for one minor version).
4. `scan --severity` splits into `--fail-on` (exit-code threshold) plus a display
   filter; `--severity` kept as a deprecated alias.
5. New exit codes `3` (config error) and `4` (internal error); `0`/`1` unchanged.
6. Inline suppressions require a `reason:`; bare suppressions emit `CG-META-001`.
   File-level `disable[…]` renamed to `ignore-file[…]` (old spelling deprecated).
7. `scan` respects `.gitignore` and a built-in skip list by default
   (`--no-gitignore` restores the previous breadth).

## [0.1.0]

Initial alpha: AST rule engine, CLI (`scan`), and five security rules
(CG-SEC-001..005) with human / JSON / SARIF output and inline suppression comments.

[Unreleased]: https://github.com/mevichitra/codeguard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mevichitra/codeguard/releases/tag/v0.1.0
