# Editors

CodeGuard ships a language server (`codeguard lsp`) and two first-party extensions that
build a native experience on it. Analysis is local in every case.

| | VS Code | Zed | Any LSP editor |
|---|---|---|---|
| Live diagnostics, coloured by severity | ✓ | ✓ | ✓ |
| Hover with data-flow path | ✓ | ✓ | ✓ |
| Quick fixes, suppressions, Explain | ✓ | ✓ | ✓ |
| Fix all in file / on save | ✓ | ✓ (`code_actions_on_format`) | ✓ (`source.fixAll.codeguard`) |
| Whole-workspace scan at startup, with progress | ✓ | ✓ | ✓ |
| Findings sidebar, status-bar counts, Security Overview | ✓ | Project Diagnostics + Markdown dashboard | — |
| Fix all in workspace, SARIF export | ✓ | — | via `codeguard/fixAll` |

Editors show **security, performance, and quality** findings by default, because
diagnostics there guide rather than gate. CI keeps the project's `categories` (security
only unless configured). Each editor can switch categories off.

## VS Code

Install the extension from [`editors/vscode`](https://github.com/mevichitra/codeguard/tree/main/editors/vscode)
(see its README) and the CLI (`pipx install codeguard-cli`).

- **Findings view** (shield icon in the activity bar). Findings are grouped by
  severity, category, or file, with a severity filter and a count badge. Inline buttons
  apply a fix or explain the rule; the context menu also suppresses a finding or copies
  its fingerprint.
- **Status bar.** `🛡 ⓧ 2 ⚠ 5 ⓘ 9`; hover for a breakdown and a *Fix all* link.
- **Security Overview** (`CodeGuard: Show Security Overview`). Totals, severity bars,
  categories, top rules, top files, and a button that applies every safe fix.
- **Fix on save:**

    ```jsonc
    "editor.codeActionsOnSave": { "source.fixAll.codeguard": "explicit" }
    ```

- **Settings:** `codeguard.categories`, `codeguard.severity.map`,
  `codeguard.rules.disable`, `codeguard.scanWorkspaceOnStartup`, `codeguard.path`.

## Zed

Install the dev extension from [`editors/zed`](https://github.com/mevichitra/codeguard/tree/main/editors/zed)
and the CLI.

- Findings appear in the editor and in **Project Diagnostics**
  (`Cmd+Shift+M` / `Ctrl+Shift+M`), which lists the whole workspace.
- The rule link in each diagnostic opens a local **Markdown dashboard**. Set
  `codeDescription` to `"help"` to open the rule documentation instead.
- Settings go under `lsp.codeguard` in `settings.json`:

    ```jsonc
    "lsp": {
      "codeguard": {
        "initialization_options": {
          "severityMap": { "medium": "error" },
          "categories": { "quality": false }
        }
      }
    },
    "languages": {
      "Python": { "code_actions_on_format": { "source.fixAll.codeguard": true } }
    }
    ```

## Other editors

Any LSP client can run `codeguard lsp` over stdio.

**Neovim 0.11+**

```lua
vim.lsp.config("codeguard", {
  cmd = { "codeguard", "lsp" },
  filetypes = { "python", "javascript", "javascriptreact", "typescript", "typescriptreact" },
  root_markers = { "codeguard.toml", "pyproject.toml", "package.json", ".git" },
  init_options = { client = "neovim", categories = { quality = false } },
})
vim.lsp.enable("codeguard")
```

**Helix** (`languages.toml`)

```toml
[language-server.codeguard]
command = "codeguard"
args = ["lsp"]
config = { client = "helix", severityMap = { info = "off" } }

[[language]]
name = "python"
language-servers = ["pyright", "codeguard"]   # keep your existing servers
```

## Server settings

Send these as `initializationOptions`, or later as `workspace/didChangeConfiguration`
with `{"settings": {"codeguard": {...}}}`. Every key is optional.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `severityMap` | object | critical/high `error`, medium `warning`, low `information`, info `hint` | Per-severity editor level. `off` hides that level. |
| `categories` | object or list | project `categories`, else all | `{ "quality": false }` or `["security", "performance"]`. |
| `rules.disable` | list | `[]` | Rule IDs hidden in the editor only. |
| `scanWorkspaceOnStartup` | bool | `true` | Scan every file at startup, not only open ones. |
| `codeDescription` | `help` \| `dashboard` | `help` | Where a diagnostic's rule link points. |
| `client` | string | — | Informational (`vscode`, `zed`, ...). |

## Protocol reference

Standard capabilities: `textDocument/publishDiagnostics` (with `relatedInformation` for
taint paths and the fix in `data`), `textDocument/hover`, `textDocument/codeAction`
(kinds `quickfix`, `source.fixAll.codeguard`, `source.codeguard.dashboard`),
`textDocument/codeLens`, `workspace/executeCommand`, and `$/progress` for workspace scans.

Commands: `codeguard.lsp.openDashboard`, `codeguard.lsp.explain` (rule ID),
`codeguard.lsp.scanWorkspace`, `codeguard.lsp.fixAll` (optional URI; sends
`workspace/applyEdit`).

Custom methods, for building editor UIs:

- **Request `codeguard/summary`** → every active finding:

    ```json
    {
      "schemaVersion": 1,
      "generatedAt": "2026-10-09T10:00:00Z",
      "workspaceRoot": "/repo",
      "counts": {"total": 3, "bySeverity": {"critical": 1, "high": 0, "medium": 0, "low": 1, "info": 1},
                 "byCategory": {"performance": 2, "security": 1}, "fixable": 2,
                 "suppressed": 0, "baselined": 0, "files": 2},
      "files": [{"uri": "file:///repo/app.py", "path": "app.py", "counts": {...},
                 "findings": [{"ruleId": "CG-SEC-011", "title": "...", "severity": "critical",
                               "category": "security", "line": 6, "col": 5, "endLine": 6, "endCol": 20,
                               "fingerprint": "...", "hasFix": false, "cwe": "CWE-78",
                               "helpUri": "...", "confidence": 0.85, "description": "..."}]}],
      "rules": [{"id": "CG-PERF-004", "title": "...", "severity": "info",
                 "category": "performance", "count": 2, "hasFix": true}]
    }
    ```

    `line` / `col` are 1-indexed, and `col` counts UTF-8 bytes (as in JSON output).
    Diagnostics use standard LSP positions (0-indexed UTF-16).

- **Notification `codeguard/summaryChanged`** `{counts}`: sent (debounced) whenever
  findings change. Re-request the summary when it arrives.
- **Request `codeguard/fixAll`** `{uri?}` → `{edit: WorkspaceEdit, count}` with every
  non-overlapping safe fix, for the client to apply.
