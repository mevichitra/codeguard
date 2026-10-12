# CG-PERF-101: await inside a loop runs the iterations one after another

**Severity:** LOW · **Category:** performance · **Languages:** JavaScript, TypeScript

## What it catches

Each iteration waits for the previous await to finish. When the iterations are independent, starting them together with Promise.all is usually much faster.

Reported:

```js
async function loadAll(ids) {
  const users = [];
  for (const id of ids) {
    users.push(await fetchUser(id));
  }
  let i = 0;
  while (i < ids.length) {
    await save(ids[i++]);
  }
  return users;
}
```

Not reported:

```js
async function loadAll(ids, stream) {
  const users = await Promise.all(ids.map(async (id) => await fetchUser(id)));
  for await (const chunk of stream) {
    await write(chunk);
  }
  return users;
}
```

## How to fix

If iterations are independent: await Promise.all(items.map(async (item) => ...)). Keep the loop when order or rate limits matter.

## Suppress

```text
// codeguard: ignore[CG-PERF-101] reason: <why this is fine>
```
