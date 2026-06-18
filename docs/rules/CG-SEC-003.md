# CG-SEC-003: Use of eval() or exec()

## Description
Detects calls to `eval()` or `exec()` with dynamic or user-controlled input. These functions execute arbitrary Python code and can be exploited to run malicious commands on the server.

## Security Risk
- **CWE**: CWE-95 — Improper Neutralization of Directives in Dynamically Evaluated Code
- **OWASP**: A03:2021 — Injection

## Vulnerable Example
```python
user_input = input("Enter expression: ")
result = eval(user_input)
```

## Safe Example
```python
import ast
result = ast.literal_eval(user_input)  # Only safe for literals
```

## Remediation
Avoid `eval()` and `exec()` entirely. Use `ast.literal_eval()` for safe literal parsing, or redesign the logic to avoid dynamic code execution.
