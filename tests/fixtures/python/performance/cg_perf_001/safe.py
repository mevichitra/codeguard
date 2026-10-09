# Outside loops, short literals, sets, and floats do not trigger.
if mode in ["r", "w", "a"]:
    pass
for x in items:
    if x in ("a", "b"):
        pass
    if x in {"a", "b", "c"}:
        pass
for x in items:
    pass
else:
    ok = x in ["a", "b", "c"]
