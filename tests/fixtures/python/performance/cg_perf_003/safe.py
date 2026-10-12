def pairs(items):
    out = []
    for i in range(len(items)):
        out.append(i * 2)
    for i, item in enumerate(items):
        out.append(item)
    return out
