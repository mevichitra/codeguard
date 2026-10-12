import tempfile
from tempfile import mktemp

path = tempfile.mktemp(suffix=".txt")
other = mktemp()
