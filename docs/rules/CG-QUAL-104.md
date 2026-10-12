# CG-QUAL-104: var declaration

**Severity:** INFO · **Category:** quality · **Languages:** JavaScript, TypeScript

## What it catches

var is function-scoped and hoisted, so a variable is visible (as undefined) before its declaration and leaks out of blocks and loops.

Reported:

```js
var count = 0;
for (var i = 0; i < 3; i++) count++;
```

Not reported:

```js
let count = 0;
const limit = 3;
for (let i = 0; i < limit; i++) count++;
```

## How to fix

Use const, or let if the variable is reassigned.

## Suppress

```text
// codeguard: ignore[CG-QUAL-104] reason: <why this is fine>
```
