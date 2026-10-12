def classify(x):
    if x == 1:
        return 1
    return {2: 2, 3: 3}.get(x, -1)
