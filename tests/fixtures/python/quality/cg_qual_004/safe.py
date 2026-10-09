def walk(tree):
    for a in tree:
        if not a:
            continue
        for b in a:
            handle(b)
