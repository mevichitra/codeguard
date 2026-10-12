# CG-QUAL-004: Code is nested too deeply

**Severity:** LOW · **Category:** quality · **Languages:** Python

## What it catches

Deeply nested blocks are hard to follow and usually hide a missing abstraction.

Reported:

```python
def walk(tree):
    for a in tree:
        if a:
            for b in a:
                if b:
                    while b:
                        if b > 1:
                            b -= 1
```

Not reported:

```python
def walk(tree):
    for a in tree:
        if not a:
            continue
        for b in a:
            handle(b)
```

## How to fix

Return early (guard clauses) and extract inner blocks into helper functions.

## Options

Set in `codeguard.toml`:

```toml
[codeguard.rules.CG-QUAL-004]
max_depth = 5
```

## Suppress

```text
# codeguard: ignore[CG-QUAL-004] reason: <why this is fine>
```
