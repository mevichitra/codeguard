# CG-SEC-107: Weak hash (MD5 / SHA-1) used for a security value

**Severity:** MEDIUM · **Category:** security · **Languages:** JavaScript, TypeScript  
**CWE:** [CWE-328](https://cwe.mitre.org/data/definitions/328.html) · **OWASP:** A02:2021 — Cryptographic Failures

## What it catches

MD5 and SHA-1 are broken for security: collisions are practical and both are fast enough to brute-force passwords. The surrounding names suggest this hash protects a password, token, or signature.

Reported:

```js
const crypto = require("crypto");

function hashPassword(password) {
  return crypto.createHash("md5").update(password).digest("hex");
}

const apiSignature = crypto.createHash("sha1").update(body).digest("hex");
```

Not reported:

```js
const crypto = require("crypto");

const etag = crypto.createHash("md5").update(body).digest("hex");
function hashPassword(password, salt) {
  return crypto.scryptSync(password, salt, 64).toString("hex");
}
const token = crypto.createHash("sha256").update(seed).digest("hex");
```

## How to fix

Hash passwords with a slow KDF (crypto.scrypt, argon2, bcrypt). For tokens and signatures use crypto.createHmac('sha256', key) or createHash('sha256').

## Suppress

```text
// codeguard: ignore[CG-SEC-107] reason: <why this is fine>
```
