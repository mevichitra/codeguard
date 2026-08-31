# SPDX-License-Identifier: Apache-2.0
"""Find and load a CodeGuard config file."""

from __future__ import annotations

import sys
from pathlib import Path

from .schema import Config, SchemaError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

_FILENAMES = ("codeguard.toml", ".codeguard.toml")


class ConfigError(Exception):
    """A config file was found but is malformed or has unknown keys."""


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from *start* (cwd by default) looking for a config file.

    Returns the first ``codeguard.toml`` / ``.codeguard.toml`` found, or the
    first ``pyproject.toml`` that contains a ``[tool.codeguard]`` table.
    """
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        for name in _FILENAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file() and _has_tool_table(pyproject):
            return pyproject
        if (directory / ".git").exists():
            break
    return None


def _has_tool_table(pyproject: Path) -> bool:
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return False
    return isinstance(data.get("tool"), dict) and "codeguard" in data["tool"]


def load_config(path: Path | None) -> Config:
    """Load and validate the config at *path*.

    ``None`` -> an empty default :class:`Config`.  Raises :class:`ConfigError`
    on a parse error or a schema violation.
    """
    if path is None:
        return Config()

    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"{path}: {exc}") from exc

    tool_table = raw.get("tool", {})
    if isinstance(tool_table, dict) and isinstance(tool_table.get("codeguard"), dict):
        table = tool_table["codeguard"]
    elif isinstance(raw.get("codeguard"), dict):
        table = raw["codeguard"]
    elif path.name == "pyproject.toml":
        table = {}
    else:
        table = raw

    if not isinstance(table, dict):
        raise ConfigError(f"{path}: [codeguard] must be a table")

    try:
        cfg = Config.from_dict(table)
    except SchemaError as exc:
        raise ConfigError(f"{path}: {exc}") from exc

    cfg.source_dir = str(path.parent)
    return cfg
