# CG-QUAL-003: Function is too complex

**Severity:** LOW · **Category:** quality · **Languages:** Python

## What it catches

High cyclomatic complexity means many paths through the code: harder to test, review, and change safely.

Reported:

```python
def classify(x):
    if x == 0:
        return 0
    if x == 1:
        return 1
    if x == 2:
        return 2
    if x == 3:
        return 3
    if x == 4:
        return 4
    if x == 5:
        return 5
    if x == 6:
        return 6
    if x == 7:
        return 7
    if x == 8:
        return 8
    if x == 9:
        return 9
    if x == 10:
        return 10
    if x == 11:
        return 11
    if x == 12:
        return 12
    if x == 13:
        return 13
    if x == 14:
        return 14
    if x == 15:
        return 15
    return -1
```

Not reported:

```python
def classify(x):
    if x == 1:
        return 1
    return {2: 2, 3: 3}.get(x, -1)
```

## How to fix

Extract branches into well-named helper functions, or use a dispatch table.

## Options

Set in `codeguard.toml`:

```toml
[codeguard.rules.CG-QUAL-003]
max_complexity = 15
```

## Suppress

```text
# codeguard: ignore[CG-QUAL-003] reason: <why this is fine>
```
