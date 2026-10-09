def add(item, bucket=None, size=0, name="x", flags=()):
    bucket = [] if bucket is None else bucket
    bucket.append(item)
    return bucket
