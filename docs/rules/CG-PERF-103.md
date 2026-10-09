# CG-PERF-103: Accumulator copied with spread inside reduce

**Severity:** LOW · **Category:** performance · **Languages:** JavaScript, TypeScript

## What it catches

Returning [...acc, x] or {...acc, k: v} from a reduce callback copies the whole accumulator on every step, which is quadratic in the number of items.

Reported:

```js
const ids = users.reduce((acc, u) => [...acc, u.id], []);
const byId = users.reduce((acc, u) => ({ ...acc, [u.id]: u }), {});
```

Not reported:

```js
const ids = users.reduce((acc, u) => {
  acc.push(u.id);
  return acc;
}, []);
const merged = items.reduce((acc, x) => [...x.tags], []);
```

## How to fix

Mutate the accumulator (acc.push(x); return acc) or use a plain loop / Object.fromEntries.

## Suppress

```text
// codeguard: ignore[CG-PERF-103] reason: <why this is fine>
```
