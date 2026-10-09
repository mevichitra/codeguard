# CG-QUAL-102: Empty catch block

**Severity:** LOW · **Category:** quality · **Languages:** JavaScript, TypeScript

## What it catches

An empty catch block discards the error. Failures become silent and very hard to diagnose.

Reported:

```js
try {
  risky();
} catch (err) {}
```

Not reported:

```js
try {
  risky();
} catch (err) {
  // optional feature: absence is fine
}
try {
  risky();
} catch (err) {
  console.error(err);
}
```

## How to fix

Handle the error, log it, or leave a comment explaining why it is safe to ignore.

## Suppress

```text
// codeguard: ignore[CG-QUAL-102] reason: <why this is fine>
```
