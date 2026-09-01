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
- **`config/`** — config discovery, schema, and monorepo nearest-wins merging.
- **`engine/discovery.py`** — `.gitignore`-aware file discovery with parallel scanning.
- **`engine/fingerprint.py`** — stable finding fingerprints for baseline and SARIF.
- **`engine/suppressions.py`** — language-aware suppression parsing with reasons and expiry.

The `Rule → Finding` contract and the `RuleRegistry` pattern are unchanged in shape; the
rule method is renamed `check` → `analyze(ctx)` and takes a context object instead of a
bare `ast` tree.
