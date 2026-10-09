# CG-PERF-105: includes() / indexOf() on an array literal inside a loop

**Severity:** LOW · **Category:** performance · **Languages:** JavaScript, TypeScript

## What it catches

Searching an array literal compares against every element on every iteration. A Set created once outside the loop answers with a single hash lookup.

Reported:

```js
for (const file of files) {
  if (["js", "jsx", "ts", "tsx"].includes(file.ext)) total++;
}
```

Not reported:

```js
const SOURCE = new Set(["js", "jsx", "ts", "tsx"]);
for (const file of files) {
  if (SOURCE.has(file.ext)) total++;
  if (["a", "b"].includes(file.ext)) total++;
}
if (["js", "jsx", "ts", "tsx"].includes(mode)) total++;
```

## How to fix

const ALLOWED = new Set([...]); outside the loop, then ALLOWED.has(x).

## Options

Set in `codeguard.toml`:

```toml
[codeguard.rules.CG-PERF-105]
min_elements = 3
```

## Suppress

```text
// codeguard: ignore[CG-PERF-105] reason: <why this is fine>
```
