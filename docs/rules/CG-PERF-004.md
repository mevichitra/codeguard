# CG-PERF-004: Redundant .keys() in iteration or membership test

**Severity:** INFO · **Category:** performance · **Languages:** Python · **Autofix:** safe ([how it works](../autofix.md))

## What it catches

Iterating a mapping or testing membership already uses its keys; calling .keys() adds a method call and a view object for nothing.

Reported:

```python
def show(config, settings):
    for key in config.keys():
        print(key)
    if "debug" in settings.options.keys():
        print("debug")
    return [k for k in config.keys() if k]
```

Not reported:

```python
def show(config):
    names = list(config.keys())
    for key in config:
        print(key)
    for key in load().keys():
        print(key)
    return names
```

## How to fix

Iterate or test the mapping itself: `for k in d:` and `k in d`.

`codeguard scan --fix` (or the editor quick fix) rewrites the example to:

```python
def show(config, settings):
    for key in config:
        print(key)
    if "debug" in settings.options:
        print("debug")
    return [k for k in config if k]
```

The autofix is applied only when it is provably equivalent: drop `.keys()` when the receiver is a name or attribute.

## Suppress

```text
# codeguard: ignore[CG-PERF-004] reason: <why this is fine>
```
