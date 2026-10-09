# CG-SEC-009: random module used for a security value

**Severity:** MEDIUM · **Category:** security · **Languages:** Python · **Autofix:** safe ([how it works](../autofix.md))  
**CWE:** [CWE-338](https://cwe.mitre.org/data/definitions/338.html) · **OWASP:** A02:2021 — Cryptographic Failures

## What it catches

The random module is not cryptographically secure: an attacker who sees some outputs can predict the rest. The surrounding names suggest this value is a token, password, or secret.

Reported:

```python
"""Tokens and passwords from the random module."""

import random
import string

ALPHABET = string.ascii_letters + string.digits


def make_password(length: int = 16) -> str:
    return "".join(random.choice(ALPHABET) for _ in range(length))


session_token = random.getrandbits(128)
otp = random.randint(100000, 999999)
```

Not reported:

```python
# Non-security randomness (simulation, shuffling, jitter) does not trigger.
import random
import secrets

dice = random.randint(1, 6)
jitter = random.uniform(0, 0.5)
deck = list(range(52))
random.shuffle(deck)
token = secrets.token_urlsafe(32)
```

## How to fix

Use the secrets module: secrets.token_urlsafe(32) for tokens, secrets.choice(seq) to pick, secrets.randbelow(n) for integers.

`codeguard scan --fix` (or the editor quick fix) rewrites the example to:

```python
"""Tokens and passwords from the random module."""

import random
import string
import secrets

ALPHABET = string.ascii_letters + string.digits


def make_password(length: int = 16) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


session_token = secrets.randbits(128)
otp = random.randint(100000, 999999)
```

The autofix is applied only when it is provably equivalent: `random.choice` -> `secrets.choice`, `random.getrandbits` -> `secrets.randbits`, `random.randbytes` -> `secrets.token_bytes` (identical signatures), adding `import secrets` when needed. Other functions get a suggestion only.

## Suppress

```text
# codeguard: ignore[CG-SEC-009] reason: <why this is fine>
```
