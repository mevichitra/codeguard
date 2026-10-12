# CG-SEC-111: Deep merge of request data (prototype pollution)

**Severity:** MEDIUM · **Category:** security · **Languages:** JavaScript, TypeScript  
**CWE:** [CWE-1321](https://cwe.mitre.org/data/definitions/1321.html) · **OWASP:** A08:2021 — Software and Data Integrity Failures

## What it catches

Request data is deep-merged into an object. A key such as '__proto__' can modify Object.prototype and change behaviour across the whole application.

Reported:

```js
const _ = require("lodash");

app.post("/settings", (req, res) => {
  _.merge(userSettings, req.body);
  $.extend(true, defaults, req.body.prefs);
});
```

Not reported:

```js
const _ = require("lodash");

app.post("/settings", (req, res) => {
  Object.assign(userSettings, { theme: req.body.theme });
  _.merge(userSettings, defaults);
  $.extend(defaults, req.body);
});
```

## How to fix

Copy only the fields you expect (const { name, email } = req.body), validate the body with a schema, or merge into Object.create(null). Keep lodash >= 4.17.21.

## Suppress

```text
// codeguard: ignore[CG-SEC-111] reason: <why this is fine>
```
