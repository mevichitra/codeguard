# CG-SEC-005: subprocess with shell=True and Variable Input

## Description
Detects calls to `subprocess.run()`, `subprocess.call()`, or `subprocess.Popen()` with `shell=True` and a dynamic (non-literal) command string. This can allow command injection if user input reaches the command.

## Security Risk
- **CWE**: CWE-78 — Improper Neutralization of Special Elements used in an OS Command
- **OWASP**: A03:2021 — Injection

## Vulnerable Example
```python
import subprocess
filename = input("Enter filename: ")
subprocess.run(f"cat {filename}", shell=True)
```

## Safe Example
```python
import subprocess
subprocess.run(["cat", filename])  # list form, no shell
```

## Remediation
Pass commands as a list instead of a string to avoid shell interpretation. If `shell=True` is required, ensure the command string is fully static and never includes user-controlled input.
