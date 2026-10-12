# CG-META-001: Suppression comment has no reason

**Severity:** LOW · **Category:** meta · **Languages:** all

## What it catches
A `codeguard: ignore[...]` comment that does not include `reason: ...`. Unexplained
suppressions rot: reviewers cannot tell why the finding was waived.

```python
eval(expr)  # codeguard: ignore[CG-SEC-003]
```

## How to fix
Add a short reason, and optionally an expiry date.

```python
eval(expr)  # codeguard: ignore[CG-SEC-003] reason: expr is a vetted constant until=2026-12-31
```

See [Suppressions](../suppressions.md).
