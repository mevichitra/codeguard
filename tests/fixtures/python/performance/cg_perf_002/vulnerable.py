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
