# Fix, suppress, review

- **Quick fix:** put the cursor on a finding and press `Ctrl+.` / `Cmd+.`. Safe fixes are
  marked as preferred.
- **Fix on save:**

  ```json
  "editor.codeActionsOnSave": { "source.fixAll.codeguard": "explicit" }
  ```

- **Suppress with a reason:** the quick-fix menu adds
  `# codeguard: ignore[CG-XXX-NNN] reason: …`. CI flags suppressions without a reason.
- **Security Overview:** totals, severity mix, top rules and files, and a one-click
  "fix all safe issues".
