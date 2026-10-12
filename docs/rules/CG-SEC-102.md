# CG-SEC-102: `child_process.exec` with a dynamic command

**Severity:** HIGH · **Category:** security · **Languages:** JavaScript, TypeScript
**CWE:** [CWE-78](https://cwe.mitre.org/data/definitions/78.html) · **OWASP:** A03:2021 — Injection

## What it catches
`child_process.exec` / `execSync` run their argument through `/bin/sh`. A non-literal
command lets an attacker inject shell syntax.

```js
const { exec } = require("child_process");
exec(`git checkout ${branch}`);
```

## How to fix
Use `execFile()` / `spawn()` with an argument array and no shell.

```js
execFile("git", ["checkout", branch]);
```
