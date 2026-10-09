# CG-SEC-013: Request data used as a file path

**Severity:** HIGH · **Category:** security · **Languages:** Python · **Analysis:** [taint tracking](../taint.md)
**CWE:** [CWE-22](https://cwe.mitre.org/data/definitions/22.html) · **OWASP:** A01:2021 — Broken Access Control

## What it catches
Request data used as the path of `open()`, `os.open/remove/unlink/rename/listdir`,
`shutil.*`, `pathlib.Path()`, or `flask.send_file()`. A name like `../../etc/passwd`
escapes the intended directory.

```python
name = request.args["file"]
return send_file(os.path.join("/srv/files", name))
```

Only request data counts. A command-line tool opening the file its user named is
expected behaviour and is not reported. `flask.send_from_directory()` is not a sink,
because it joins paths safely.

## How to fix
```python
from werkzeug.utils import secure_filename
name = secure_filename(request.args["file"])         # or os.path.basename()

path = (BASE / name).resolve()
if not path.is_relative_to(BASE):
    abort(404)
```
