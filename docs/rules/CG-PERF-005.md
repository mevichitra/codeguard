# CG-PERF-005: Regular expression compiled inside a loop

**Severity:** INFO · **Category:** performance · **Languages:** Python

## What it catches

A regular expression with a constant pattern is compiled (or looked up in re's cache) on every iteration. Compile it once outside the loop.

Reported:

```python
import re
from re import compile as rx


def emails(lines):
    out = []
    for line in lines:
        if re.match(r"[^@]+@[^@]+", line):
            out.append(line)
        pattern = rx("^#")
    return out
```

Not reported:

```python
import re

EMAIL = re.compile(r"[^@]+@[^@]+")


def emails(lines, user_pattern):
    out = [line for line in lines if EMAIL.match(line)]
    for line in lines:
        if re.search(user_pattern, line):
            out.append(line)
    return out
```

## How to fix

Compile once outside the loop: PATTERN = re.compile(r'...'), then PATTERN.search(s).

## Suppress

```text
# codeguard: ignore[CG-PERF-005] reason: <why this is fine>
```
