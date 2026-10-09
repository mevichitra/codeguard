# Roadmap

CodeGuard grows in phases. Each phase keeps the 2.0 stability contract: rule IDs, the
`Finding` / JSON schema, config keys, and exit codes only ever gain additions.

## Phase 1 — 2.2 (this release)

- **Security depth:** intraprocedural [taint tracking](taint.md) for Python with five
  source-to-sink rules (SQL, shell, eval, path traversal, open redirect), plus new pattern
  rules for weak hashes, disabled TLS verification, insecure randomness, and Express
  redirect / path-traversal sinks.
- **Performance and quality rule packs** for Python and JavaScript / TypeScript.
- **Safe autofix:** `codeguard scan --fix`, `--fix-dry-run`, and editor quick fixes.
- **Editors:** severity-aware diagnostics, quick fixes, hovers, a fix-all code action, a
  VS Code Findings sidebar and Security Overview, and Zed settings passthrough.

## Phase 2 — 2.3

- **JavaScript / TypeScript taint tracking.** Sources `req.*`, `location.*`,
  `process.argv`; sinks from CG-SEC-101/102/103/109/110.
- **Same-file function summaries.** Track which parameters of a function reach its
  return value, and recognise helper functions that sanitize.
- **Pattern rules confirmed by taint** gain confidence and severity when a source is
  found.
- **Custom rules** in a Semgrep-compatible YAML subset (`pattern`, `pattern-either`,
  `pattern-not`, `metavariable-regex`), loaded from the `rule_paths` config key.
- **New security rules:** SSRF, CSRF exemptions, ReDoS-prone regexes, XXE, insecure
  cookies, JWT `none` algorithm or disabled verification, raw SQL through ORMs.
- **Distribution:** VS Code Marketplace and Open VSX publishing; the Zed extension
  downloads a standalone server binary from GitHub Releases.
- **Overview trends:** keep summary snapshots so the editor overview can chart findings
  over time.
- **`codeguard serve --watch`:** a long-running daemon that shares the language server's
  incremental cache with other tools.
- **Zed context server (MCP)** exposing the workspace summary to Zed's assistant. Zed
  removed extension slash commands, so this replaces a `/codeguard` command.

## Phase 3 — 3.0

- Go, Java, and Rust through tree-sitter.
- Offline triage that fills `Finding.triage` (heuristics first: test files, sanitizer
  proximity; an optional local model later).
- Standalone binaries and a Homebrew tap.
- Cross-file analysis backed by a workspace symbol index.
