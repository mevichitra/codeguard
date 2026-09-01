# CodeGuard for Zed

This development extension starts the local CodeGuard language server and shows
security findings as native Zed diagnostics.

## Development setup

1. Install this checkout so the `codeguard` executable is on your shell `PATH`:

   ```bash
   pipx install -e .
   # or
   uv tool install -e .
   ```

2. In Zed, open Extensions, choose **Install Dev Extension**, and select this
   `editors/zed` directory.
3. Open a Python, JavaScript, JSX, TypeScript, or TSX project. CodeGuard scans the
   workspace and refreshes the active document after edits.

The development extension checks the shell `PATH` first and then the current
worktree's `.venv/bin/codeguard`. For other environments, launch Zed from a
shell where the command is available or add the tool installation directory to
your shell `PATH`.
