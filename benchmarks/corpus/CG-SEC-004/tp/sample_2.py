# CG-SEC-004 tp sample 2: marshal.loads
import marshal

def load_bytecode(data):
    # VULNERABLE
    return marshal.loads(data)

code = load_bytecode(untrusted_bytes)
