import tempfile

fd, path = tempfile.mkstemp(suffix=".txt")
with tempfile.NamedTemporaryFile(delete=False) as fh:
    name = fh.name
