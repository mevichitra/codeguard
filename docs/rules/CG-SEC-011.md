# CG-SEC-011: Untrusted input reaches a shell command

**Severity:** CRITICAL · **Category:** security · **Languages:** Python · **Analysis:** [taint tracking](../taint.md)
**CWE:** [CWE-78](https://cwe.mitre.org/data/definitions/78.html) · **OWASP:** A03:2021 — Injection

## What it catches
Untrusted data in a command run through the shell: `os.system`, `os.popen`,
`subprocess.getoutput` / `getstatusoutput`, and `subprocess.*` with `shell=True`.
Replaces [CG-SEC-005](CG-SEC-005.md) on the same line.

```python
host = request.form["host"]
os.system("ping -c 1 " + host)   # host = "8.8.8.8; rm -rf ~"
```

Request data gives confidence 0.85. Process input (`sys.argv`, environment, `input()`)
gives 0.6, since only the invoking user controls it.

## How to fix
```python
subprocess.run(["ping", "-c", "1", host])        # no shell
os.system("ping -c 1 " + shlex.quote(host))      # if a shell is unavoidable
```
