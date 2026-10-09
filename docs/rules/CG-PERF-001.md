# CG-PERF-001: Membership test against a list literal inside a loop

**Severity:** LOW · **Category:** performance · **Languages:** Python · **Autofix:** safe ([how it works](../autofix.md))

## What it catches

`x in [...]` compares x against every element, on every iteration. A set literal `{...}` finds it with a single hash lookup.

Reported:

```python
# Membership tests against list / tuple literals inside loops.
def count_sources(paths):
    n = 0
    for p in paths:
        if p.suffix.lower() in [".py", ".pyi", ".pyx"]:
            n += 1
        if str(p) not in (".", "..", "/"):
            n += 1
        if p in ["a", "b", "c"]:
            n += 1
    return n
```

Not reported:

```python
# Outside loops, short literals, sets, and floats do not trigger.
if mode in ["r", "w", "a"]:
    pass
for x in items:
    if x in ("a", "b"):
        pass
    if x in {"a", "b", "c"}:
        pass
for x in items:
    pass
else:
    ok = x in ["a", "b", "c"]
```

## How to fix

Use a set literal, or hoist a frozenset constant out of the loop.

`codeguard scan --fix` (or the editor quick fix) rewrites the example to:

```python
# Membership tests against list / tuple literals inside loops.
def count_sources(paths):
    n = 0
    for p in paths:
        if p.suffix.lower() in {".py", ".pyi", ".pyx"}:
            n += 1
        if str(p) not in {".", "..", "/"}:
            n += 1
        if p in ["a", "b", "c"]:
            n += 1
    return n
```

The autofix is applied only when it is provably equivalent: rewrite the literal as a set when every element is a hashable constant (str / int / bytes / bool / None -- no floats, whose NaN and -0.0 compare differently) **and** the left operand is evidently hashable (a literal, an f-string, `str()` / `int()` / `len()` / `ord()` / `repr()`, or a string method such as `.lower()`). Anything else gets a suggestion only, because `unhashable in {...}` raises `TypeError`.

## Options

Set in `codeguard.toml`:

```toml
[codeguard.rules.CG-PERF-001]
min_elements = 3
```

## Suppress

```text
# codeguard: ignore[CG-PERF-001] reason: <why this is fine>
```
