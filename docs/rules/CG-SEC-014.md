# CG-SEC-014: Request data used as a redirect target

**Severity:** MEDIUM · **Category:** security · **Languages:** Python · **Analysis:** [taint tracking](../taint.md)
**CWE:** [CWE-601](https://cwe.mitre.org/data/definitions/601.html) · **OWASP:** A01:2021 — Broken Access Control

## What it catches
A redirect whose URL comes from the request: `flask.redirect()`, Django `redirect()` /
`HttpResponseRedirect()`, and Starlette / FastAPI `RedirectResponse()`.

```python
return redirect(request.args.get("next"))   # ?next=https://evil.example
```

## How to fix
Redirect only to relative paths or an allow-list of hosts. Django provides
`url_has_allowed_host_and_scheme()`. Allow-list checks are not visible to the analysis;
suppress with a reason once the check is in place.
