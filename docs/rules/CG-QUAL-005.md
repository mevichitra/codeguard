# CG-QUAL-005: Function takes too many parameters

**Severity:** INFO · **Category:** quality · **Languages:** Python

## What it catches

Long parameter lists are easy to call wrongly and suggest the function does too much.

Reported:

```python
def connect(host, port, user, password, database, timeout, retries, ssl, *, verbose=False):
    pass
```

Not reported:

```python
class Client:
    def connect(self, host, port, user, password, database, timeout, retries, ssl):
        pass
```

## How to fix

Group related parameters into a dataclass, or split the function.

## Options

Set in `codeguard.toml`:

```toml
[codeguard.rules.CG-QUAL-005]
max_params = 8
```

## Suppress

```text
# codeguard: ignore[CG-QUAL-005] reason: <why this is fine>
```
