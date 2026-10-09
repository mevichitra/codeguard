# CG-SEC-109: Redirect to a URL taken from the request

**Severity:** MEDIUM · **Category:** security · **Languages:** JavaScript, TypeScript  
**CWE:** [CWE-601](https://cwe.mitre.org/data/definitions/601.html) · **OWASP:** A01:2021 — Broken Access Control

## What it catches

The redirect target comes from the request or the page URL. Attackers use this to send victims from a trusted domain to a phishing site (open redirect).

Reported:

```js
app.get("/login/done", (req, res) => {
  res.redirect(req.query.next);
});

app.post("/go", (req, res) => res.redirect(302, req.body.url));

const target = new URLSearchParams(location.search).get("return");
location.href = new URLSearchParams(location.search).get("return");
```

Not reported:

```js
app.get("/login/done", (req, res) => {
  res.redirect("/home");
});
location.href = "/dashboard";
```

## How to fix

Redirect only to relative paths or an allow-list of origins, e.g. const u = new URL(next, base); if (u.origin === base) res.redirect(u.pathname).

## Suppress

```text
// codeguard: ignore[CG-SEC-109] reason: <why this is fine>
```
