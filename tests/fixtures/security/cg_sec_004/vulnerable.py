# Fixture: CG-SEC-004 vulnerable
# This file MUST trigger CG-SEC-004 (unsafe deserialization).

import pickle
import marshal
import yaml


def load_session(data: bytes) -> object:
    # VULNERABLE: pickle.loads on arbitrary bytes
    return pickle.loads(data)


def load_model(file_path: str) -> object:
    # VULNERABLE: pickle.load from a file
    with open(file_path, "rb") as f:
        return pickle.load(f)


def load_binary(data: bytes) -> object:
    # VULNERABLE: marshal.loads
    return marshal.loads(data)


def parse_config(config_str: str) -> dict:
    # VULNERABLE: yaml.load without Loader
    return yaml.load(config_str)


def parse_config_v2(config_str: str) -> dict:
    # VULNERABLE: yaml.load with FullLoader (not safe for untrusted input)
    return yaml.load(config_str, Loader=yaml.FullLoader)
