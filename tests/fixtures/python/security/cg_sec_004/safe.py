# Fixture: CG-SEC-004 safe
# This file MUST NOT trigger CG-SEC-004.

import json
import yaml


def parse_config_safe_loader(config_str: str) -> dict:
    # SAFE: yaml.load with SafeLoader
    return yaml.load(config_str, Loader=yaml.SafeLoader)


def parse_config_safe_load(config_str: str) -> dict:
    # SAFE: yaml.safe_load is the preferred API
    return yaml.safe_load(config_str)


def parse_config_positional(config_str: str) -> dict:
    # SAFE: SafeLoader passed as positional argument
    return yaml.load(config_str, yaml.SafeLoader)


def load_json_data(raw: str) -> dict:
    # SAFE: JSON deserialization — no arbitrary object instantiation
    return json.loads(raw)
