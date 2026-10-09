# CodeGuard

Static analysis that finds security anti-patterns in source code — fast, offline, and
built to sit at every gate of your workflow (editor, pre-commit, pre-push, PR/CI, merge,
scheduled audit) from a single config file.

!!! note "Version 2.2"
    CodeGuard scans **Python, JavaScript, and TypeScript** for **security** issues
    (including source-to-sink [taint tracking](taint.md) for Python), **performance**
    problems, and **code-quality** risks. Many findings come with a safe
    [autofix](autofix.md). The [VS Code and Zed extensions](editors.md) show everything
    live with quick fixes. Rule IDs, the `Finding` / JSON schema, config keys, and exit
    codes are a stable contract from 2.0, and upgrading never changes a CI exit code:
    `scan` and `ci` run security rules unless you opt into more categories.

## What it produces

Each finding carries a stable rule ID, a severity, a CWE/OWASP mapping, a precise
location, and a plain-English fix suggestion. Output is human-readable text, JSON, or
[SARIF 2.1.0](output-formats.md) for GitHub code scanning.

```
myproject/auth.py:12:5  [CG-SEC-001] HIGH  SQL query built with string formatting
    12 | cursor.execute(f"SELECT * FROM users WHERE id = {uid}")
         ^
  → Use parameterized queries: cursor.execute("SELECT ... WHERE id = %s", (uid,))

1 finding(s)  (1 high)
```

## Rules

| Category | Python | JavaScript / TypeScript |
|---|---|---|
| **Security** | SQL injection, shell injection, `eval`/`exec`, unsafe deserialization, hardcoded secrets, weak hashes, disabled TLS verification, `random` for secrets, `tempfile.mktemp`, and taint-tracked SQL / shell / eval / path traversal / open redirect | `eval` / `new Function`, `child_process.exec`, DOM XSS, `dangerouslySetInnerHTML`, hardcoded secrets, `Math.random()` for secrets, weak hashes, disabled TLS verification, open redirect, path traversal, prototype pollution |
| **Performance** | list-literal membership in loops, `+=` string building, `range(len())`, redundant `.keys()`, regex compiled in loops | `await` in loops, JSON deep clone, spread in `reduce`, `new RegExp` in loops, array-literal lookups in loops |
| **Quality** | mutable defaults, swallowed exceptions, complexity, nesting depth, parameter count | loose equality, empty `catch`, complexity, `var` |

See the [rules overview](rules/index.md) or run `codeguard list-rules`.

## Next steps

- [Workflow & Value guide](workflow.md)
- [Install](install.md)
- [Usage](usage.md)
- [Editors](editors.md)
- [CI integration](ci.md)
