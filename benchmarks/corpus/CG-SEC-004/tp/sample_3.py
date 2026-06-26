# CG-SEC-004 tp sample 3: yaml.load with no SafeLoader
import yaml

def load_config(path):
    with open(path) as f:
        # VULNERABLE: unsafe yaml.load
        return yaml.load(f)
