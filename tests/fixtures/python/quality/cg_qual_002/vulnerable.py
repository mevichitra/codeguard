def load(path):
    try:
        return open(path).read()
    except:
        pass
    try:
        return int(path)
    except Exception:
        ...
