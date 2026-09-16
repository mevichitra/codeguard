# CG-SEC-004 tn sample 3: yaml.safe_load (safe)
import yaml

def load_config(path):
    with open(path) as f:
        # SAFE
        return yaml.safe_load(f)
