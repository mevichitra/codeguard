# CG-SEC-004 tn sample 2: json.loads (safe)
import json

def load_config(data):
    # SAFE
    return json.loads(data)

config = load_config('{"key": "value"}')
