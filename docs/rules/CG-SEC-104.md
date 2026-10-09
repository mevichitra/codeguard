# CG-SEC-104: `dangerouslySetInnerHTML` with a non-literal value

**Severity:** HIGH · **Category:** security · **Languages:** JavaScript, TypeScript (JSX/TSX)
**CWE:** [CWE-79](https://cwe.mitre.org/data/definitions/79.html) · **OWASP:** A03:2021 — Injection

## What it catches
`<div dangerouslySetInnerHTML={{ __html: value }} />` with a non-literal `value`,
which bypasses React's XSS escaping.

## How to fix
Render the value as text, or sanitize it with DOMPurify before passing it to `__html`.

```jsx
<div>{comment.body}</div>
```
