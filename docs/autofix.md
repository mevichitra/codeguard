# Autofix

Some findings come with a **safe fix**: a rewrite that provably keeps the program's
behaviour. CodeGuard applies safe fixes only. When a rewrite might change behaviour
(for example `==` to `===` on values of unknown type), the finding keeps a suggestion
and no fix.

## Command line

```bash
codeguard scan src/ --fix-dry-run      # print the fixes as a unified diff, change nothing
codeguard scan src/ --fix              # apply them, then report what is left
```

- `--fix` edits files in place, rescans them, and computes the exit code from what remains.
  A fully fixed tree exits `0`.
- `--fix-dry-run` exits as a normal scan would, so it can gate CI ("fixable issues exist").
- Both respect suppressions and the baseline: muted findings are never rewritten.
- Line endings, encoding, and every byte outside the edited span are preserved.
- When two fixes overlap, the first is applied and the other is reported as skipped. Run
  `--fix` again to pick it up.
- `--fix` cannot be combined with stdin (`-`).

JSON output carries each fix under `fix` and counts them in `summary.fixable`. SARIF
output includes them as `fixes`, which GitHub code scanning shows as suggestions.

## Editors

- **Quick fix:** put the cursor on a finding and open the code-action menu
  (VS Code `Ctrl+.` / `Cmd+.`, Zed `Ctrl+.` / `Cmd+.`). The fix is the preferred action.
- **Fix all in a file:** the `source.fixAll.codeguard` code action. Run it on save:

    ```jsonc
    // VS Code settings.json
    "editor.codeActionsOnSave": { "source.fixAll.codeguard": "explicit" }
    ```

    ```jsonc
    // Zed settings.json
    "languages": {
      "Python": { "code_actions_on_format": { "source.fixAll.codeguard": true } }
    }
    ```

- **Fix all in the workspace:** VS Code command **CodeGuard: Fix All Safe Issues in Workspace**.

## Rules with a safe fix

| Rule | Rewrite | Applied when |
|---|---|---|
| [CG-SEC-009](rules/CG-SEC-009.md) | `random.choice` / `getrandbits` / `randbytes` → `secrets.choice` / `randbits` / `token_bytes`, adding `import secrets` | the value is security-sensitive; signatures are identical |
| [CG-PERF-001](rules/CG-PERF-001.md) | `x in [a, b, c]` → `x in {a, b, c}` | elements are hashable constants and `x` is evidently hashable |
| [CG-PERF-004](rules/CG-PERF-004.md) | `for k in d.keys()` → `for k in d` | the receiver is a name or attribute |
| [CG-QUAL-101](rules/CG-QUAL-101.md) | `==` / `!=` → `===` / `!==` | both sides have the same evident type (`typeof x == "string"`, `a.length != 0`) |

```bash
codeguard list-rules --fixable
```

## Writing a rule with a fix

Attach a `Fix` to the finding and set `autofix = True` on the rule:

```python
from codeguard.engine.finding import Fix
from codeguard.engine.fixes import edit_for_ast_node

fix = Fix("Remove .keys()", (edit_for_ast_node(call, receiver_text),))
findings.append(self._make_finding(node=call, filename=filename, fix=fix))
```

Edit positions are 1-indexed lines and UTF-8 byte columns, end-exclusive, exactly as
`ast` and tree-sitter report them. Add a `fixed.*` fixture next to `vulnerable.*`: the
test suite applies the fixes and compares the result byte for byte.
