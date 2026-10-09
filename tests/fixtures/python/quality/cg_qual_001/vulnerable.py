def add(item, bucket=[]):
    bucket.append(item)
    return bucket


def merge(a, *, extra={}, seen=set()):
    return {**a, **extra}
