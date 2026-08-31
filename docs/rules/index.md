# Rules

Every rule has a stable ID (`CG-<CATEGORY>-<NNN>`), a severity, a CWE/OWASP mapping, and
a fix suggestion. IDs are permanent — never renumbered or reused.

The `1xx` block covers JavaScript / TypeScript; `0xx` covers Python.

| ID | Title | Severity | CWE | Languages |
|---|---|---|---|---|
| CG-SEC-001 | SQL query built with string formatting | HIGH | CWE-89 | Python |
| CG-SEC-002 | Hardcoded secret | HIGH | CWE-798 | Python |
| CG-SEC-003 | `eval()` / `exec()` on dynamic input | HIGH | CWE-95 | Python |
| CG-SEC-004 | Unsafe deserialization | HIGH | CWE-502 | Python |
| CG-SEC-005 | `subprocess` with `shell=True` and a dynamic command | HIGH | CWE-78 | Python |
| CG-SEC-101 | Dynamic code execution (`eval` / `Function` / string timer) | HIGH | CWE-95 | JS, TS |
| CG-SEC-102 | `child_process.exec` with a dynamic command | HIGH | CWE-78 | JS, TS |
| CG-SEC-103 | DOM XSS sink assigned a non-literal (`innerHTML`, `document.write`, …) | HIGH | CWE-79 | JS, TS |
| CG-SEC-104 | `dangerouslySetInnerHTML` with a non-literal value | HIGH | CWE-79 | JS, TS |
| CG-SEC-105 | Hardcoded secret | HIGH | CWE-798 | JS, TS |
| CG-SEC-106 | `Math.random()` used for a security value | MEDIUM | CWE-338 | JS, TS |

```bash
codeguard list-rules
codeguard list-rules --language javascript
codeguard explain CG-SEC-101
```

!!! note "v2.0"
    This table will be **generated** from rule metadata (the same source
    `codeguard explain` reads), with a page per rule.
