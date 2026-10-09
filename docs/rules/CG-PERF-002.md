# CG-PERF-002: String built with += inside a loop

**Severity:** LOW · **Category:** performance · **Languages:** Python

## What it catches

Repeated `s += ...` on a string inside a loop can copy the whole string each time, which is quadratic in its final length.

Reported:

```python
def render(rows):
    html = ""
    for row in rows:
        html += f"<tr><td>{row}</td></tr>"
    return html


def csv_line(cells):
    out: str = ""
    i = 0
    while i < len(cells):
        out += cells[i] + ","
        i += 1
    return out
```

Not reported:

```python
def total(values):
    s = 0
    for v in values:
        s += v
    return s


def render(rows):
    parts = []
    for row in rows:
        parts.append(f"<tr><td>{row}</td></tr>")
    return "".join(parts)
```

## How to fix

Collect the parts in a list and join once: parts.append(x); ... ''.join(parts).

## Suppress

```text
# codeguard: ignore[CG-PERF-002] reason: <why this is fine>
```
