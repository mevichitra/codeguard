# CG-SEC-004 tn sample 1: using json instead of pickle (safe)
import json

def load_session(data):
    # SAFE: json.loads is safe for untrusted data
    return json.loads(data)
