# CodeGuard for Zed

Runs the local CodeGuard language server and shows its findings as native Zed
diagnostics: security (with taint tracking), performance, and code quality for Python,
JavaScript, JSX, TypeScript, and TSX. Nothing leaves your machine.

## What you get

- **Diagnostics coloured by severity.** Critical and high are errors, medium are
  warnings, low and info are hints.
- **Hovers** that explain each finding and, for taint findings, show the data flow from
  untrusted input to the dangerous call.
- **Code actions** (`Cmd+.` / `Ctrl+.`): safe quick fixes, *Suppress on this line*,
  *Suppress in this file*, *Explain rule*, *Fix all CodeGuard issues in this file*, and
  *Open CodeGuard Dashboard*.
- **Project Diagnostics** (`Cmd+Shift+M` / `Ctrl+Shift+M`) is the workspace dashboard:
  CodeGuard scans every file at startup, not only open ones.
- **Markdown dashboard:** click a rule link in a diagnostic, or use the dashboard code
  action, to open a report with totals and every finding. It is stored in the user
  cache, not the repository.

## Setup

1. Install the CLI so `codeguard` is on your shell `PATH`, or in the project's `.venv`:

   ```bash
   pipx install codeguard-cli        # or: uv tool install codeguard-cli
   ```

2. In Zed, open **Extensions**, choose **Install Dev Extension**, and select this
   `editors/zed` directory.

The extension looks for `codeguard` in `lsp.codeguard.binary.path`, then `.venv/` or
`venv/` in the worktree (`bin/` on macOS/Linux, `Scripts\` on Windows), then `PATH`.

## Settings

All keys are optional. Add them to Zed's `settings.json`:

```jsonc
{
  "lsp": {
    "codeguard": {
      "binary": { "path": "/opt/tools/codeguard" },
      "initialization_options": {
        // error | warning | information | hint | off
        "severityMap": { "medium": "error", "info": "off" },
        // Unset categories follow `categories` in codeguard.toml; otherwise all are shown.
        "categories": { "quality": false },
        // Hide rules in the editor only. CI keeps using codeguard.toml.
        "rules": { "disable": ["CG-QUAL-104"] },
        // Rule links open the docs site instead of the Markdown dashboard.
        "codeDescription": "help"
      }
    }
  },
  // Apply every safe CodeGuard fix when formatting
  "languages": {
    "Python": { "code_actions_on_format": { "source.fixAll.codeguard": true } },
    "TypeScript": { "code_actions_on_format": { "source.fixAll.codeguard": true } }
  }
}
```

Project-wide settings (excludes, baselines, rule options, suppression policy) live in
`codeguard.toml` and apply in Zed as well.

## Notes

- Zed removed extension-provided slash commands, so there is no `/codeguard` assistant
  command. A Model Context Protocol server exposing the workspace summary is on the
  [roadmap](../../docs/roadmap.md).

## Building

```bash
rustup target add wasm32-wasip2
cargo build --release --target wasm32-wasip2
cargo test        # host-side unit tests for the settings merge and path logic
```
