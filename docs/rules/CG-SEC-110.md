# CG-SEC-110: File path built from request data

**Severity:** HIGH · **Category:** security · **Languages:** JavaScript, TypeScript  
**CWE:** [CWE-22](https://cwe.mitre.org/data/definitions/22.html) · **OWASP:** A01:2021 — Broken Access Control

## What it catches

A file path is built from request data. Sequences like '../' let an attacker read or overwrite files outside the intended directory (path traversal).

Reported:

```ts
import fs from "fs";
import path from "path";

app.get("/file", (req, res) => {
  const data = fs.readFileSync(path.join(__dirname, "files", req.query.name as string));
  res.send(data);
});

app.get("/download/:name", (req, res) => {
  res.download(`/srv/files/${req.params.name}`);
});

app.delete("/upload", async (req, res) => {
  await fs.promises.unlink("/tmp/" + req.body.file);
});
```

Not reported:

```ts
import fs from "fs";
import path from "path";

app.get("/file", (req, res) => {
  const data = fs.readFileSync(path.join(__dirname, "files", path.basename(req.query.name as string)));
  res.sendFile(req.params.name, { root: "/srv/files" });
  fs.readFileSync("/etc/app/config.json");
});
```

## How to fix

Reduce the value to a file name with path.basename(), then resolve it and check it stays inside the base directory: if (!full.startsWith(base + path.sep)) reject.

## Suppress

```text
// codeguard: ignore[CG-SEC-110] reason: <why this is fine>
```
