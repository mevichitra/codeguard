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
