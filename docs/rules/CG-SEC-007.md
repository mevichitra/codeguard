# CG-SEC-007: TLS certificate verification disabled

**Severity:** HIGH · **Category:** security · **Languages:** Python  
**CWE:** [CWE-295](https://cwe.mitre.org/data/definitions/295.html) · **OWASP:** A07:2021 — Identification and Authentication Failures

## What it catches

Certificate verification is turned off, so the connection accepts any certificate. Anyone on the network path can read and modify the traffic.

Reported:

```python
# TLS certificate verification turned off.
import ssl

import httpx
import requests

requests.get("https://internal.example", verify=False)
client = httpx.Client(verify=False)
ctx = ssl._create_unverified_context()

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE


def fetch(session):
    return session.post("https://api.example", json={}, verify=False)
```

Not reported:

```python
# Verification on, or a custom CA bundle.
import ssl

import requests

requests.get("https://internal.example", verify="/etc/ssl/internal-ca.pem")
requests.get("https://example.com")
context = ssl.create_default_context(cafile="ca.pem")
context.verify_mode = ssl.CERT_REQUIRED
options = {"verify": False}  # a plain dict, not a request
```

## How to fix

Keep certificate verification on. To trust a private CA, pass its bundle: requests.get(url, verify='/path/to/ca.pem') or ssl.create_default_context(cafile=...).

## Suppress

```text
# codeguard: ignore[CG-SEC-007] reason: <why this is fine>
```
