# Changelog

All notable changes to the CodeGuard Zed extension are documented here. The extension is
versioned separately from the `codeguard-cli` package; the CLI's own changes are in the
[main changelog](https://github.com/mevichitra/codeguard/blob/main/CHANGELOG.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
extension follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - Unreleased

Requires `codeguard-cli` 2.2.0 or newer.

### Added

- Settings under `lsp.codeguard` in Zed's `settings.json` now reach the server, both as
  `initialization_options` and as `settings`: `severityMap`, `categories`,
  `rules.disable`, `scanWorkspaceOnStartup`, and `codeDescription`.
- `lsp.codeguard.binary` can set the executable's path, arguments, and extra
  environment variables.
- The manifest declares CodeGuard's `quickfix`, `source.fixAll.codeguard`, and
  `source.codeguard.dashboard` code-action kinds, so `code_actions_on_format` can apply
  every safe fix.
- Diagnostics are coloured by severity, hovers show the taint data-flow path, and quick
  fixes, suppressions, and an Explain action are available. These come from the 2.2
  language server.

### Fixed

- `.venv\Scripts\codeguard.exe` and `venv\Scripts\codeguard.exe` are found on Windows.
- The extension now also looks in `venv/`, not only `.venv/`.

## [0.1.0] - 2026-09-01

Development release, installed with *Install Dev Extension*.

### Added

- Starts `codeguard lsp` for Python, JavaScript, JSX, TypeScript, and TSX, using
  `.venv/bin/codeguard` in the worktree or `codeguard` on `PATH`.
