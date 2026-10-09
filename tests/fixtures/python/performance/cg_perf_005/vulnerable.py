import re
from re import compile as rx


def emails(lines):
    out = []
    for line in lines:
        if re.match(r"[^@]+@[^@]+", line):
            out.append(line)
        pattern = rx("^#")
    return out
