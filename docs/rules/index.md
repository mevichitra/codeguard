# Rules

Every rule has a stable ID (`CG-<CATEGORY>-<NNN>`), a severity, a CWE/OWASP mapping, and
a fix suggestion. IDs are permanent — never renumbered or reused.

| ID | Title | Severity | Category | CWE | Languages |
|---|---|---|---|---|---|
| CG-SEC-001 | SQL query built with string formatting | HIGH | security | CWE-89 | Python |
| CG-SEC-002 | Hardcoded secret | HIGH | security | CWE-798 | Python |
| CG-SEC-003 | `eval()` / `exec()` on dynamic input | HIGH | security | CWE-95 | Python |
| CG-SEC-004 | Unsafe deserialization | HIGH | security | CWE-502 | Python |
| CG-SEC-005 | `subprocess` with `shell=True` and a dynamic command | HIGH | security | CWE-78 | Python |

!!! note "v2.0"
    This table will be **generated** from rule metadata (the same source `codeguard
    explain <ID>` reads), with a page per rule covering rationale, examples, false
    positives, and suppression. JavaScript and TypeScript rules join the list.

List rules from the CLI:

```bash
codeguard --version   # today
codeguard list-rules  # v2.0
```
