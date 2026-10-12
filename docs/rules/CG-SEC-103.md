# CG-SEC-103: DOM XSS sink assigned a non-literal

**Severity:** HIGH · **Category:** security · **Languages:** JavaScript, TypeScript
**CWE:** [CWE-79](https://cwe.mitre.org/data/definitions/79.html) · **OWASP:** A03:2021 — Injection

## What it catches
`el.innerHTML = x`, `el.outerHTML = x`, `el.insertAdjacentHTML(pos, x)`, and
`document.write(x)` / `writeln(x)` where the HTML is not a string literal.

```js
results.innerHTML = "<b>" + query + "</b>";
```

## How to fix
Set `textContent`, build nodes with DOM APIs, or sanitize with DOMPurify first.

```js
results.textContent = query;
results.innerHTML = DOMPurify.sanitize(html); // codeguard: ignore[CG-SEC-103] reason: sanitized
```
