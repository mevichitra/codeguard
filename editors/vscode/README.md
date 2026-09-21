# CodeGuard for Visual Studio Code

Official VS Code extension for **CodeGuard** — providing fast, local, offline security diagnostics for **Python, JavaScript, JSX, TypeScript, and TSX**.

## Features

- **Live Security Diagnostics**: Detects security vulnerabilities and anti-patterns as you type and save.
- **Rule Documentation & Fixes**: Diagnostics include rule IDs, descriptions, and recommended fixes.
- **Interactive Markdown Dashboard**: Click the rule link in a diagnostic or run **Open CodeGuard Dashboard** to view a full project security report.
- **Code Lens**: Status summary on the first line of your source files displaying total workspace warnings with one-click access to the dashboard.
- **Automatic Environment Detection**: Automatically detects `codeguard` installed in your workspace virtual environment (`.venv/bin/codeguard` or Windows `.venv\Scripts\codeguard.exe`) or on your system `PATH`.
- **Zero Cloud Dependencies**: 100% offline analysis. No code leaves your computer.

---

## Installation & Setup

### 1. Install CodeGuard CLI

The extension requires the `codeguard` CLI tool. Install it globally or in your virtual environment:

```bash
# Recommended: install with pipx or uv
pipx install codeguard-cli
# or:
uv tool install codeguard-cli

# Or install from source:
pip install -e .
```

### 2. Development Setup / Running from Source

1. Clone or open the CodeGuard repository in VS Code:
   ```bash
   cd editors/vscode
   npm install
   npm run compile
   ```
2. Press `F5` in VS Code to launch a new **Extension Development Host** window with the CodeGuard extension loaded.
3. Open any Python, JavaScript, JSX, TypeScript, or TSX workspace. CodeGuard will start automatically and provide live diagnostics.

### 3. Packaging into a `.vsix`

To generate a standalone `.vsix` extension package:

```bash
cd editors/vscode
npx @vscode/vsce package --no-git-tag-version
```

Then in VS Code:
1. Open the Extensions view (`Ctrl+Shift+X` or `Cmd+Shift+X`).
2. Click the `...` menu (Views and More Actions) at the top right of the Extensions pane.
3. Choose **Install from VSIX...** and select the `.vsix` file.

---

## Configuration Settings

You can customize CodeGuard in VS Code settings (`settings.json`):

| Setting | Type | Default | Description |
|---|---|---|---|
| `codeguard.enable` | `boolean` | `true` | Enable or disable the CodeGuard language server. |
| `codeguard.path` | `string` | `""` | Custom path to the `codeguard` binary (if not in PATH or `.venv`). |
| `codeguard.trace.server` | `string` | `"off"` | Trace language server communication (`off`, `messages`, `verbose`). |

---

## Commands

- **CodeGuard: Open Dashboard** (`codeguard.openDashboard`): Generates and opens the latest Markdown security report in VS Code.
- **CodeGuard: Restart Server** (`codeguard.restartServer`): Restarts the CodeGuard language server process.

---

## License

Apache-2.0.
