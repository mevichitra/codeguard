# CG-PERF-104: new RegExp() with a constant pattern inside a loop

**Severity:** LOW · **Category:** performance · **Languages:** JavaScript, TypeScript

## What it catches

A regular expression with a constant pattern is compiled on every iteration. Create it once outside the loop, or use a regex literal.

Reported:

```js
for (const line of lines) {
  if (new RegExp("^\\s*#").test(line)) continue;
}
```

Not reported:

```js
const COMMENT = /^\s*#/;
for (const line of lines) {
  if (COMMENT.test(line)) continue;
  if (new RegExp(userPattern).test(line)) count++;
}
```

## How to fix

Hoist it: const PATTERN = /.../; before the loop.

## Suppress

```text
// codeguard: ignore[CG-PERF-104] reason: <why this is fine>
```
