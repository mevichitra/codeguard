# CG-QUAL-103: Function is too complex

**Severity:** LOW · **Category:** quality · **Languages:** JavaScript, TypeScript

## What it catches

High cyclomatic complexity means many paths through the code: harder to test, review, and change safely.

Reported:

```js
function classify(x) {
  if (x === 0) return 0;
  if (x === 1) return 1;
  if (x === 2) return 2;
  if (x === 3) return 3;
  if (x === 4) return 4;
  if (x === 5) return 5;
  if (x === 6) return 6;
  if (x === 7) return 7;
  if (x === 8) return 8;
  if (x === 9) return 9;
  if (x === 10) return 10;
  if (x === 11) return 11;
  if (x === 12) return 12;
  if (x === 13) return 13;
  if (x === 14) return 14;
  if (x === 15) return 15;
  return -1;
}
```

Not reported:

```js
function classify(x) {
  return { 1: 1, 2: 2 }[x] ?? -1;
}
```

## How to fix

Extract branches into well-named helper functions, or use a lookup object instead of long if/else chains.

## Options

Set in `codeguard.toml`:

```toml
[codeguard.rules.CG-QUAL-103]
max_complexity = 15
```

## Suppress

```text
// codeguard: ignore[CG-QUAL-103] reason: <why this is fine>
```
