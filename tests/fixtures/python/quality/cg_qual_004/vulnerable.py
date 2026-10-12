def walk(tree):
    for a in tree:
        if a:
            for b in a:
                if b:
                    while b:
                        if b > 1:
                            b -= 1
