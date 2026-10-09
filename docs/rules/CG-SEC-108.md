# CG-SEC-108: TLS certificate verification disabled

**Severity:** HIGH · **Category:** security · **Languages:** JavaScript, TypeScript  
**CWE:** [CWE-295](https://cwe.mitre.org/data/definitions/295.html) · **OWASP:** A07:2021 — Identification and Authentication Failures

## What it catches

Certificate verification is turned off, so the connection accepts any certificate. Anyone on the network path can read and modify the traffic.

Reported:

```js
const https = require("https");

const agent = new https.Agent({ rejectUnauthorized: false });
request({ url, strictSSL: false });
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
```

Not reported:

```js
const https = require("https");
const fs = require("fs");

const agent = new https.Agent({ rejectUnauthorized: true, ca: fs.readFileSync("ca.pem") });
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "1";
```

## How to fix

Keep verification on. To trust a private CA, pass it explicitly: new https.Agent({ ca: fs.readFileSync('ca.pem') }) or NODE_EXTRA_CA_CERTS.

## Suppress

```text
// codeguard: ignore[CG-SEC-108] reason: <why this is fine>
```
