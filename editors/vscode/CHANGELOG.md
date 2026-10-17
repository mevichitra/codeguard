# Changelog

All notable changes to the CodeGuard VS Code extension are documented here. The
extension is versioned separately from the `codeguard-cli` package; the CLI's own
changes are in the [main changelog](https://github.com/mevichitra/codeguard/blob/main/CHANGELOG.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
extension follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - Unreleased

Requires `codeguard-cli` 2.2.0 or newer.

### Added

- **Findings view** in the activity bar: every finding in the workspace, grouped by
  severity, category, or file, with a severity filter, a count badge, and inline
  *Apply Quick Fix* and *Explain Rule* buttons. The context menu also suppresses a
  finding on its line or copies its fingerprint.
- **Status-bar counts** of blocking, warning, and informational findings, with a tooltip
  breakdown and links to fix everything or open the overview.
- **Security Overview** panel: totals, severity bars, categories, top rules, top files,
  and a button that applies every safe fix.
- Commands to fix all safe issues in the current file or the whole workspace, rescan
  the workspace, and export a SARIF report.
- Settings: `codeguard.categories`, `codeguard.severity.map`, `codeguard.rules.disable`,
  `codeguard.scanWorkspaceOnStartup`, `codeguard.sarif.outputPath`, and
  `codeguard.showEditorTitleButton`.
- A *Get started with CodeGuard* walkthrough with a sample vulnerable file.
- Diagnostics are coloured by severity, hovers show the taint data-flow path, and quick
  fixes, suppressions, and fix-all on save (`source.fixAll.codeguard`) are available.
  These come from the 2.2 language server.

### Changed

- The minimum VS Code version is now 1.82, which `vscode-languageclient` 9 already
  required; the extension would not start on older versions.
- The extension now uses its own CodeGuard output channel and shows setup help in the
  Findings view when the `codeguard` executable is missing.

### Fixed

- The extension's `codeguard.openDashboard` command no longer collides with the
  command of the same name that the language server registered.
- The status-bar spinner no longer spins forever when the server stops or fails, or
  when a scan never reports new results.
- `LICENSE` now carries the verbatim Apache License 2.0 text, so licence scanners
  detect the extension as Apache-2.0. The terms are unchanged.

## [0.1.0] - 2026-09-24

Development release, not published to the Marketplace.

### Added

- Starts `codeguard lsp` for Python, JavaScript, JSX, TypeScript, and TSX, finding the
  executable in `codeguard.path`, the workspace `.venv` / `venv`, or `PATH`.
- Commands to open the Markdown dashboard and restart the server; a status-bar item;
  `codeguard.enable`, `codeguard.path`, and `codeguard.trace.server` settings.
