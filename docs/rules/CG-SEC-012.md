# CG-SEC-012: Untrusted input reaches `eval()` / `exec()`

**Severity:** CRITICAL · **Category:** security · **Languages:** Python · **Analysis:** [taint tracking](../taint.md)
**CWE:** [CWE-95](https://cwe.mitre.org/data/definitions/95.html) · **OWASP:** A03:2021 — Injection

## What it catches
Untrusted data passed to `eval()`, `exec()`, or `compile()`. Replaces
[CG-SEC-003](CG-SEC-003.md) on the same line.

```python
expr = request.json["expr"]
result = eval(expr)
```

## How to fix
Never execute input as code. Parse data with `json.loads()` or `ast.literal_eval()`, and
dispatch with a dict of allowed functions.
