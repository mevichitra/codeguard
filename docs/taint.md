# Taint tracking

Pattern rules see one expression at a time: `os.system("ls " + name)` is suspicious
whatever `name` is. Taint tracking follows **where the data came from**. It reports a
sink only when untrusted data actually reaches it, and shows the path.

```text
app.py:11:5  [CG-SEC-011] CRITICAL  Untrusted input reaches a shell command
    11 |     os.system(cmd)
  ↳ line 9: Untrusted input: flask request.form
  ↳ line 9: Flows through: host = request.form["host"]
  ↳ line 10: Flows through: cmd = "ping -c 1 " + host
```

## Rules

| Rule | Sink | Replaces |
|---|---|---|
| [CG-SEC-010](rules/CG-SEC-010.md) | SQL `execute()` | CG-SEC-001 |
| [CG-SEC-011](rules/CG-SEC-011.md) | shell commands | CG-SEC-005 |
| [CG-SEC-012](rules/CG-SEC-012.md) | `eval` / `exec` / `compile` | CG-SEC-003 |
| [CG-SEC-013](rules/CG-SEC-013.md) | file paths (request data only) | — |
| [CG-SEC-014](rules/CG-SEC-014.md) | redirects (request data only) | — |

When a taint rule and its pattern sibling fire on the same line, only the taint finding
is kept. It has the higher severity and the explanation. If the taint rule is disabled,
the pattern rule reports as before.

## Sources

| Kind | Examples | Confidence |
|---|---|---|
| Request data (`web`) | `flask.request.args/form/json/values/headers/cookies/files/data/...`, `request.get_json()`, Django/DRF `request.GET/POST/body/data/query_params/META/COOKIES` (also `self.request`), parameters of functions decorated with `@app.route`, `@router.get/post/...`, `@api_view` | 0.85 |
| Process input (`local`) | `sys.argv`, `os.environ`, `os.getenv()`, `input()`, `sys.stdin` | 0.6 |

Import aliases are resolved, so `from flask import request as rq` works.

## Propagation

Taint flows through:

- assignments, augmented assignments, tuple unpacking, and the walrus operator;
- f-strings, `%` formatting, `.format()`, `+`, and `" ".join(...)`;
- method calls on a tainted value (`.strip()`, `.get()`, `.decode()`, `.lower()`, ...),
  except ones that return a bool or position (`.isdigit()`, `.startswith()`, `.find()`);
- `str()`, `os.path.join()`, `pathlib.Path()`, `urllib.parse.unquote()`, `json.loads()`,
  `base64.b64decode()`, and similar;
- containers: writing a tainted value into `d[k]` taints `d`;
- loops (a value tainted at the end of one iteration reaches the next), and both arms of
  `if` / `try` / `match`.

## Sanitizers

Wrapping a value in any of these makes it clean: `int()`, `float()`, `bool()`, `len()`,
`shlex.quote()`, `html.escape()`, `markupsafe.escape()`, `urllib.parse.quote()`,
`re.escape()`, `os.path.basename()`, `werkzeug.utils.secure_filename()`, `bleach.clean()`.

## Limits

- **Intraprocedural.** Calls to your own functions return clean values. A helper that
  returns `request.args["x"]` is not followed. Same-file function summaries are on the
  [roadmap](roadmap.md).
- **Validation checks are invisible.** `if name in ALLOWED:` does not clean `name`.
  Suppress the finding with a reason once you have such a check.
- **Python only.** JavaScript and TypeScript taint tracking is planned.
