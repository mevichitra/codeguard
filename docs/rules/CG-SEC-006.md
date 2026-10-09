# CG-SEC-006: Weak hash (MD5 / SHA-1) used for a security value

**Severity:** MEDIUM · **Category:** security · **Languages:** Python  
**CWE:** [CWE-328](https://cwe.mitre.org/data/definitions/328.html) · **OWASP:** A02:2021 — Cryptographic Failures

## What it catches

MD5 and SHA-1 are broken for security purposes: collisions are practical and both are fast enough to brute-force passwords. The surrounding names suggest this hash protects a password, token, or signature.

Reported:

```python
# MD5 / SHA-1 protecting passwords and tokens.
import hashlib
from hashlib import sha1


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def make_reset_token(user_id: int) -> str:
    return sha1(str(user_id).encode()).hexdigest()


api_signature = hashlib.new("MD5", b"payload").hexdigest()
```

Not reported:

```python
# Checksums, cache keys, opted-out calls, and strong hashes do not trigger.
import hashlib


def cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def file_checksum(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def legacy_password_lookup(password: str) -> str:
    return hashlib.md5(password.encode(), usedforsecurity=False).hexdigest()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
```

## How to fix

Hash passwords with a slow, salted KDF (hashlib.scrypt, argon2, bcrypt). For tokens and signatures use hashlib.sha256 or hmac with SHA-256. If this is not security-related, pass usedforsecurity=False.

## Suppress

```text
# codeguard: ignore[CG-SEC-006] reason: <why this is fine>
```
