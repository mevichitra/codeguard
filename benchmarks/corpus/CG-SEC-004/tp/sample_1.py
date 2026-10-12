# CG-SEC-004 tp sample 1: pickle.loads on untrusted data
import pickle

def load_session(data):
    # VULNERABLE
    return pickle.loads(data)

session = load_session(input_bytes)
