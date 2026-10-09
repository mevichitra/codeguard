# CodeGuard for Visual Studio Code

Security, performance, and code-quality analysis for **Python, JavaScript, and
TypeScript**, right in the editor. Everything runs locally; no code leaves your machine.

## Features

- **Diagnostics as you type**, coloured by severity: critical and high are errors, medium
  are warnings, low and info are hints. Change the mapping with `codeguard.severity.map`.
- **Taint tracking for Python.** When untrusted input reaches SQL, a shell, `eval`, a file
  path, or a redirect, the hover and the Problems panel show the whole path, from
  `request.args` to the dangerous call.
- **Quick fixes** (`Ctrl+.` / `Cmd+.`) for rules with a safe rewrite, plus
  **Suppress on this line**, **Suppress in this file**, and **Explain rule**.
- **Fix all:** run **CodeGuard: Fix All Safe Issues in File / Workspace**, or fix on save:

  ```jsonc
  "editor.codeActionsOnSave": { "source.fixAll.codeguard": "explicit" }
  ```

- **Findings view** in the activity bar. It groups every finding in the workspace by
  severity, category, or file, filters by severity, and has inline fix and explain buttons.
- **Status bar** with live counts. Its tooltip breaks them down and links to fixes.
- **Security Overview** (`CodeGuard: Show Security Overview`): totals, severity bars,
  categories, top rules, top files, and a one-click fix for all safe issues.
- **Export SARIF** for GitHub code scanning or other tools.
- A **Get started** walkthrough with a sample vulnerable file.

## Requirements

Install the CodeGuard CLI (Python 3.10+):

```bash
pipx install codeguard-cli        # or: uv tool install codeguard-cli
```

The extension looks for `codeguard` in `codeguard.path`, then the workspace `.venv` /
`venv`, then `PATH` (including `~/.local/bin`, Homebrew, and pyenv shims).

## Settings

| Setting | Default | |
|---|---|---|
| `codeguard.enable` | `true` | Run the language server. |
| `codeguard.path` | `""` | Path to the `codeguard` executable. |
| `codeguard.categories` | `{}` | Per-category switches, e.g. `{ "quality": false }`. Unset categories follow `categories` in `codeguard.toml`; without it, all are shown. |
| `codeguard.severity.map` | `{}` | e.g. `{ "medium": "error", "info": "off" }`. |
| `codeguard.rules.disable` | `[]` | Rule IDs hidden in the editor only. CI keeps using `codeguard.toml`. |
| `codeguard.scanWorkspaceOnStartup` | `true` | Scan all files at startup, not only open ones. |
| `codeguard.sarif.outputPath` | `""` | Default file name for **Export SARIF Report**. |
| `codeguard.showEditorTitleButton` | `false` | Show an overview button in the editor title bar. |
| `codeguard.trace.server` | `off` | Log LSP traffic to the CodeGuard output channel. |

Project settings such as excludes, baselines, rule options, and suppression policy live
in `codeguard.toml` and apply in the editor too.

## Building from source

```bash
cd editors/vscode
npm ci
npm test              # compiles, then runs unit tests
npx @vscode/vsce package
```

Press `F5` in VS Code to launch an Extension Development Host, or install the `.vsix`
with **Extensions: Install from VSIX…**. Requires VS Code 1.82 or newer.
