# CG-PERF-003: for i in range(len(seq)) used to index seq

**Severity:** INFO · **Category:** performance · **Languages:** Python

## What it catches

The loop iterates over indices only to look items up with seq[i]. Iterating the sequence directly (or with enumerate) avoids a lookup per item.

Reported:

```python
def total(items):
    s = 0
    for i in range(len(items)):
        s += items[i]
    return s
```

Not reported:

```python
def pairs(items):
    out = []
    for i in range(len(items)):
        out.append(i * 2)
    for i, item in enumerate(items):
        out.append(item)
    return out
```

## How to fix

Iterate directly: for item in seq, or for i, item in enumerate(seq).

## Suppress

```text
# codeguard: ignore[CG-PERF-003] reason: <why this is fine>
```
