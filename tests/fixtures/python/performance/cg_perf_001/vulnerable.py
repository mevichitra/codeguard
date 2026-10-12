# Membership tests against list / tuple literals inside loops.
def count_sources(paths):
    n = 0
    for p in paths:
        if p.suffix.lower() in [".py", ".pyi", ".pyx"]:
            n += 1
        if str(p) not in (".", "..", "/"):
            n += 1
        if p in ["a", "b", "c"]:
            n += 1
    return n
