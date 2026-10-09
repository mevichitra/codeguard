# CG-SEC-008: Insecure temporary file name (tempfile.mktemp)

**Severity:** MEDIUM · **Category:** security · **Languages:** Python  
**CWE:** [CWE-377](https://cwe.mitre.org/data/definitions/377.html) · **OWASP:** A01:2021 — Broken Access Control

## What it catches

tempfile.mktemp() returns a file name without creating the file. Between the call and the open, another process can create or symlink that path (a race).

Reported:

```python
import tempfile
from tempfile import mktemp

path = tempfile.mktemp(suffix=".txt")
other = mktemp()
```

Not reported:

```python
import tempfile

fd, path = tempfile.mkstemp(suffix=".txt")
with tempfile.NamedTemporaryFile(delete=False) as fh:
    name = fh.name
```

## How to fix

Create the file atomically: tempfile.NamedTemporaryFile(delete=False), tempfile.mkstemp(), or tempfile.mkdtemp() for a private directory.

## Suppress

```text
# codeguard: ignore[CG-SEC-008] reason: <why this is fine>
```
