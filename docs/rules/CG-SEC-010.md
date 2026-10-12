# CG-SEC-010: Untrusted input reaches a SQL query

**Severity:** HIGH · **Category:** security · **Languages:** Python · **Analysis:** [taint tracking](../taint.md)
**CWE:** [CWE-89](https://cwe.mitre.org/data/definitions/89.html) · **OWASP:** A03:2021 — Injection

## What it catches
Request data or process input that flows, through any number of assignments and string
operations, into `cursor.execute()` / `executemany()` / `executescript()`.

```python
from flask import request

def search(db):
    term = request.args.get("q")                    # source
    sql = "SELECT * FROM items WHERE name = '" + term + "'"
    db.execute(sql)                                 # sink -> CG-SEC-010
```

The finding lists the source and every assignment on the way, in the terminal, SARIF
(`relatedLocations`), and editor diagnostics. On the same line it replaces the pattern
rule [CG-SEC-001](CG-SEC-001.md), so you get one finding with the full path.

## How to fix
Pass values as query parameters.

```python
db.execute("SELECT * FROM items WHERE name = ?", (term,))
```

Wrapping the value in `int()` / `float()` is recognised as sanitizing.
