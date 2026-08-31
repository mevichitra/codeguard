# SPDX-License-Identifier: Apache-2.0
"""Configuration: ``codeguard.toml`` / ``pyproject.toml [tool.codeguard]``."""

from __future__ import annotations

from .loader import ConfigError, find_config, load_config
from .schema import Config, RuleOverride, RuleSettings

__all__ = [
    "Config",
    "ConfigError",
    "RuleOverride",
    "RuleSettings",
    "find_config",
    "load_config",
]
