# Install the CodeGuard CLI

CodeGuard's analysis runs in a small local language server. Nothing is uploaded.

```bash
pipx install codeguard-cli        # or: uv tool install codeguard-cli
```

The extension finds `codeguard` in this order:

1. the `codeguard.path` setting,
2. `.venv/` or `venv/` in the workspace,
3. your `PATH` (including `~/.local/bin`, Homebrew, and pyenv shims).

Once the status bar shows the shield with counts, you are ready.
