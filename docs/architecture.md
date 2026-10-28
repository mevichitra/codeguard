# Architecture

```
discovery  →  language adapter (parse)  →  rules (analyze)  →  findings
                                                                  │
                          suppressions · baseline · severity  ────┤
                                                                  ▼
                              formatter (human · json · sarif · …)
```

## Components

- **`engine/registry.py`** — `RuleRegistry`, the catalogue of rules. Rules self-register
  at import time; duplicate IDs are a hard error. The module-level `REGISTRY` singleton is
  what the runner uses.
- **`engine/rule.py`** — the `Rule` base class. A rule detects exactly one concern, is
  self-contained, and holds no state between files.
- **`engine/finding.py`** — `Finding`, `Location`, `Severity`, `Category`. `Finding` is a
  frozen dataclass and the atomic unit of output.
- **`engine/runner.py`** — `AnalysisRunner` walks the filesystem, parses each file, runs
  the active rules, applies suppressions, and returns findings.
- **`analysis.py`** — project-level configuration, discovery, baseline, and policy orchestration
  shared by editor integrations and CLI behavior.
- **`lsp/`** — a dependency-free stdio language server that publishes CodeGuard findings as
  native editor diagnostics for saved and in-memory source.
- **`cli/`** — the `codeguard` command (`click`) and the output formatters.
- **`rules/`** — built-in rules, grouped by category. Each is one file plus a
  vulnerable/safe fixture pair under `tests/fixtures/`.

## v2.0 additions

- **`lang/`** — a language adapter layer. `LanguageSupport` implementations wrap a parser
  (stdlib `ast` for Python; tree-sitter for JavaScript and TypeScript) and hand rules a
  uniform `SourceNode`. Rules declare the languages they target.
- **`config/`** — config discovery (first `codeguard.toml` / `.codeguard.toml` / `pyproject.toml [tool.codeguard]` found walking up to the repository root) and the validated schema.
- **`engine/discovery.py`** — `.gitignore`-aware file discovery with parallel scanning.
- **`engine/fingerprint.py`** — the `codeguard/v1` finding fingerprint, kept for SARIF and old baselines.
- **`engine/identity.py`**, **`engine/matcher.py`**, **`engine/filepairs.py`** — the `codeguard/v2` identity record, the one-to-one multi-pass matcher and the pairing of files across renames that `engine/baseline.py` builds on. See [Finding identity](identity.md).
- **`engine/suppressions.py`** — language-aware suppression parsing with reasons and expiry.

The `Rule → Finding` contract and the `RuleRegistry` pattern are unchanged in shape; the
rule method is renamed `check` → `analyze(ctx)` and takes a context object instead of a
bare `ast` tree.

## v2.2 additions

```text
            ┌──────────── codeguard.toml (categories, rule options, ...) ───────────┐
files ──▶ discovery ──▶ parse ──▶ dataflow (Python, lazy) ──▶ rules ──▶ supersedes ──▶ policy ──▶ output
                                                                │                                  │
                                                         Finding.fix / .related          CLI · SARIF · LSP
```

- **`engine/dataflow/`**: intraprocedural taint analysis for Python. `catalog.py` lists
  sources, sanitizers, and propagators. `python.py` walks each scope once and records
  the taint of every expression. The runner computes it once per file, and only when an
  active rule sets `wants_dataflow`. Rules query it through `ctx.dataflow.taint_of(node)`.
- **`Rule.supersedes`**: after all rules run, a finding from a rule that supersedes
  another removes that rule's finding on the same line. That is how a taint finding
  (with its path) replaces the matching pattern finding without the rules knowing about
  each other.
- **`engine/fixes.py`**: safe autofixes. Rules attach `Fix(edits=...)`. Edits are
  applied to UTF-8 bytes, atomically per fix, skipping overlaps. The CLI (`--fix`) and
  the language server (`source.fixAll.codeguard`) share it.
- **Rule options**: `Rule.default_options`, overridden per project under
  `[rules.<ID>]`, validated against the declared names and types, and available as
  `ctx.option(name)`.
- **Categories**: `categories` in the config (default security for `scan` / `ci`, all in
  editors) selects which rule packs run.
- **`lsp/`**: `actions.py` (settings, diagnostics, code actions, hovers), `positions.py`
  (UTF-8 byte ↔ UTF-16 conversion), `summary.py` (`codeguard/summary`), and `server.py`
  (protocol, scheduling, caching). See [Editors](editors.md) for the protocol.
