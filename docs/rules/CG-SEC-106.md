# CG-SEC-106: `Math.random()` used for a security value

**Severity:** MEDIUM · **Category:** security · **Languages:** JavaScript, TypeScript
**CWE:** [CWE-338](https://cwe.mitre.org/data/definitions/338.html)

## What it catches
`Math.random()` used to build a token, session id, password, nonce, salt, OTP, or API
key. The rule fires only when the surrounding binding name signals a security use
(confidence 0.8).

```js
const resetToken = Math.random().toString(36).slice(2);
```

## How to fix
Use a cryptographically secure source.

```js
const resetToken = crypto.randomUUID();
const bytes = crypto.getRandomValues(new Uint8Array(32));
```
