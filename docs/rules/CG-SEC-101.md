# CG-SEC-101: Dynamic code execution

**Severity:** HIGH · **Category:** security · **Languages:** JavaScript, TypeScript
**CWE:** [CWE-95](https://cwe.mitre.org/data/definitions/95.html) · **OWASP:** A03:2021 — Injection

## What it catches
`eval(x)`, `new Function(..., body)`, and `setTimeout("...")` / `setInterval("...")`
where the code string is not a literal. Passing a string to a timer is an implicit `eval`.

```js
eval(userInput);
const fn = new Function("a", body);
setTimeout("refresh(" + id + ")", 1000);
```

## How to fix
Do not execute strings as code. Use a lookup table of functions, dynamic `import()`,
or pass a function (not a string) to `setTimeout` / `setInterval`.

```js
const handlers = { refresh, reload };
handlers[name]?.();
setTimeout(() => refresh(id), 1000);
```

## Suppress
```js
eval(trusted); // codeguard: ignore[CG-SEC-101] reason: build-time constant
```
