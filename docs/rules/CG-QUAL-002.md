# CG-QUAL-002: Exception silently swallowed

**Severity:** LOW · **Category:** quality · **Languages:** Python

## What it catches

A bare `except:` or `except Exception:` whose body is only `pass` hides every error, including bugs, and makes failures impossible to diagnose. A bare `except:` also catches KeyboardInterrupt and SystemExit.

Reported:

```python
def load(path):
    try:
        return open(path).read()
    except:
        pass
    try:
        return int(path)
    except Exception:
        ...
```

Not reported:

```python
import logging


def load(path):
    try:
        return open(path).read()
    except FileNotFoundError:
        pass
    except Exception:
        logging.exception("could not read %s", path)
        raise
```

## How to fix

Catch the specific exception you expect, and log or re-raise anything else: except ValueError: logger.warning(...).

## Suppress

```text
# codeguard: ignore[CG-QUAL-002] reason: <why this is fine>
```
