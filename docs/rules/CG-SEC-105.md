# CG-SEC-105: Hardcoded secret

**Severity:** HIGH · **Category:** security · **Languages:** JavaScript, TypeScript
**CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html) · **OWASP:** A07:2021 — Identification and Authentication Failures

## What it catches
A non-trivial string literal assigned to an identifier, property, or object key whose
name reads like a credential (`password`, `apiKey`, `token`, `clientSecret`, …).
Mirrors the Python rule [CG-SEC-002](CG-SEC-002.md). Confidence is 0.9 because
placeholder values in examples can trip it.

```js
const apiKey = "sk_live_51H8...";
```

## How to fix
Load secrets from `process.env` or a secrets manager; never commit them.

```js
const apiKey = process.env.STRIPE_API_KEY;
```
