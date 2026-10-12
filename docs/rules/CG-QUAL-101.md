# CG-QUAL-101: Loose equality (== / !=)

**Severity:** LOW · **Category:** quality · **Languages:** JavaScript, TypeScript · **Autofix:** safe ([how it works](../autofix.md))

## What it catches

== and != convert types before comparing ('' == 0 and '0' == false are both true). Strict === and !== compare without conversion.

Reported:

```js
if (typeof value == "string") run();
if (items.length != 0) run();
if (status == 200) run();
```

Not reported:

```js
if (value == null) run();
if (value != undefined) run();
if (status === 200) run();
```

## How to fix

Use === (convert explicitly first if needed).

`codeguard scan --fix` (or the editor quick fix) rewrites the example to:

```js
if (typeof value === "string") run();
if (items.length !== 0) run();
if (status == 200) run();
```

## Suppress

```text
// codeguard: ignore[CG-QUAL-101] reason: <why this is fine>
```
