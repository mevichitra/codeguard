# CodeGuard

Static analysis that finds security anti-patterns in source code — fast, offline, and
built to sit at every gate of your workflow (editor, pre-commit, pre-push, PR/CI, merge,
scheduled audit) from a single config file.

!!! warning "Status: alpha, heading to v2.0"
    CodeGuard scans **Python, JavaScript, and TypeScript**. Still on the **v2.0**
    road: baseline/diff scanning, a CI-native command, and packaged distribution
    (pre-commit hook, GitHub Action, Docker image, standalone binaries). Public
    interfaces are not yet stable — see [Migrating to v2](migration-v2.md).

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

## Rules today

**Python** (`0xx`): SQL string-formatting (CWE-89), hardcoded secrets (CWE-798),
`eval`/`exec` on dynamic input (CWE-95), unsafe deserialization (CWE-502),
`subprocess` shell injection (CWE-78).

**JavaScript / TypeScript** (`1xx`): dynamic code execution (CWE-95),
`child_process` shell injection (CWE-78), DOM XSS sinks (CWE-79),
`dangerouslySetInnerHTML` (CWE-79), hardcoded secrets (CWE-798),
`Math.random()` for security values (CWE-338).

See [Rules overview](rules/index.md) or run `codeguard list-rules`.

## Next steps

- [Install](install.md)
- [Usage](usage.md)
- [CI integration](ci.md)
