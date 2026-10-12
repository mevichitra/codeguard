import re

EMAIL = re.compile(r"[^@]+@[^@]+")


def emails(lines, user_pattern):
    out = [line for line in lines if EMAIL.match(line)]
    for line in lines:
        if re.search(user_pattern, line):
            out.append(line)
    return out
