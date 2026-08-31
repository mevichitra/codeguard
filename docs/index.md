# CodeGuard

Static analysis that finds security anti-patterns in source code — fast, offline, and
built to sit at every gate of your workflow (editor, pre-commit, pre-push, PR/CI, merge,
scheduled audit) from a single config file.

!!! warning "Status: alpha, heading to v2.0"
    Today CodeGuard scans **Python** with five security rules. The **v2.0** line adds
    JavaScript and TypeScript, a config file, baseline/diff scanning, a CI-native command,
    and packaged distribution (pre-commit hook, GitHub Action, Docker image, standalone
    binaries). Public interfaces are not yet stable — see [Migrating to v2](migration-v2.md).

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

| ID | Catches | Severity | CWE |
|---|---|---|---|
| CG-SEC-001 | SQL built with f-strings / `%` / `.format()` / concat | HIGH | CWE-89 |
| CG-SEC-002 | Hardcoded passwords, API keys, tokens | HIGH | CWE-798 |
| CG-SEC-003 | `eval()` / `exec()` / `compile()` on non-literal input | HIGH | CWE-95 |
| CG-SEC-004 | `pickle` / `marshal` / `yaml.load` without a safe loader | HIGH | CWE-502 |
| CG-SEC-005 | `subprocess(..., shell=True)` with a dynamic command | HIGH | CWE-78 |

See [Rules overview](rules/index.md).

## Next steps

- [Install](install.md)
- [Usage](usage.md)
- [CI integration](ci.md)
