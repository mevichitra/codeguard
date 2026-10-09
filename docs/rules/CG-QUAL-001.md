# CG-QUAL-001: Mutable default argument

**Severity:** MEDIUM · **Category:** quality · **Languages:** Python

## What it catches

A default value is created once, when the function is defined, and shared by every call. Mutating it in one call leaks state into the next.

Reported:

```python
def add(item, bucket=[]):
    bucket.append(item)
    return bucket


def merge(a, *, extra={}, seen=set()):
    return {**a, **extra}
```

Not reported:

```python
def add(item, bucket=None, size=0, name="x", flags=()):
    bucket = [] if bucket is None else bucket
    bucket.append(item)
    return bucket
```

## How to fix

Default to None and create the value inside: def f(items=None): items = [] if items is None else items

## Suppress

```text
# codeguard: ignore[CG-QUAL-001] reason: <why this is fine>
```
