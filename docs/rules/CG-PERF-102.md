# CG-PERF-102: Deep clone with JSON.parse(JSON.stringify(x))

**Severity:** INFO · **Category:** performance · **Languages:** JavaScript, TypeScript

## What it catches

Serialising to a JSON string and parsing it back is slow for large objects and silently drops undefined, functions, Dates (become strings), Maps, and Sets.

Reported:

```js
const copy = JSON.parse(JSON.stringify(state));
```

Not reported:

```js
const copy = structuredClone(state);
const parsed = JSON.parse(text);
```

## How to fix

Use structuredClone(x) (Node 17+, all modern browsers). It keeps Dates, Maps, and Sets, but throws on functions.

## Suppress

```text
// codeguard: ignore[CG-PERF-102] reason: <why this is fine>
```
