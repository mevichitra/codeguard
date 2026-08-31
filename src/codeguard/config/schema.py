# SPDX-License-Identifier: Apache-2.0
"""The ``codeguard.toml`` schema, as validated dataclasses.

A single ``[tool.codeguard]`` table (or the top-level table of a standalone
``codeguard.toml``) maps to :class:`Config`.  :func:`Config.from_dict` validates
and raises :class:`~codeguard.config.loader.ConfigError` with a precise message
on anything unknown or malformed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from codeguard.engine.finding import Severity
from codeguard.lang.base import Language

_SEVERITIES = {s.value for s in Severity}
_LANGUAGES = {lang.value for lang in Language}


class SchemaError(Exception):
    """A schema violation, re-raised as ConfigError by the loader."""


def _expect_str_list(value: Any, key: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise SchemaError(f"{key!r} must be a list of strings")
    return list(value)


def _expect_bool(value: Any, key: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaError(f"{key!r} must be true or false")
    return value


def _expect_severity(value: Any, key: str) -> str:
    if value not in _SEVERITIES:
        raise SchemaError(f"{key!r} must be one of {sorted(_SEVERITIES)}, got {value!r}")
    return str(value)


@dataclass
class RuleSettings:
    """Per-rule tuning from ``[tool.codeguard.rules.<ID>]``."""

    severity: str | None = None
    confidence_min: float | None = None

    @classmethod
    def from_dict(cls, rule_id: str, data: dict[str, Any]) -> RuleSettings:
        out = cls()
        for k, v in data.items():
            if k == "severity":
                out.severity = _expect_severity(v, f"rules.{rule_id}.severity")
            elif k == "confidence_min":
                if not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
                    raise SchemaError(f"rules.{rule_id}.confidence_min must be in [0.0, 1.0]")
                out.confidence_min = float(v)
            else:
                raise SchemaError(f"unknown key rules.{rule_id}.{k}")
        return out


@dataclass
class RuleOverride:
    """A path-scoped override from ``[[tool.codeguard.overrides]]``."""

    path: str
    disable: list[str] = field(default_factory=list)
    enable: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleOverride:
        if "path" not in data or not isinstance(data["path"], str):
            raise SchemaError("each [[overrides]] needs a string 'path'")
        out = cls(path=data["path"])
        for k, v in data.items():
            if k == "path":
                continue
            if k == "disable":
                out.disable = _expect_str_list(v, "overrides.disable")
            elif k == "enable":
                out.enable = _expect_str_list(v, "overrides.enable")
            else:
                raise SchemaError(f"unknown key overrides.{k}")
        return out


@dataclass
class Config:
    """The whole ``[tool.codeguard]`` table."""

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    gitignore: bool = True
    fail_on: str = "info"
    output: str = "human"
    jobs: int = 0  # 0 = auto
    baseline: str | None = None
    rule_paths: list[str] = field(default_factory=list)
    enable: list[str] = field(default_factory=list)
    disable: list[str] = field(default_factory=list)
    severity_remap: dict[str, str] = field(default_factory=dict)
    rules: dict[str, RuleSettings] = field(default_factory=dict)
    overrides: list[RuleOverride] = field(default_factory=list)
    #: Directory the config was loaded from (for resolving relative paths).
    source_dir: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        out = cls()
        known = {f.name for f in fields(cls)} - {
            "rules",
            "overrides",
            "source_dir",
            "enable",
            "disable",
        }
        for key, value in data.items():
            if key in ("include", "exclude", "languages", "rule_paths"):
                lst = _expect_str_list(value, key)
                if key == "languages":
                    bad = set(lst) - _LANGUAGES
                    if bad:
                        raise SchemaError(f"unknown language(s): {sorted(bad)}")
                setattr(out, key, lst)
            elif key == "gitignore":
                out.gitignore = _expect_bool(value, key)
            elif key == "fail_on":
                if value != "never":
                    _expect_severity(value, key)
                out.fail_on = str(value)
            elif key == "output":
                if value not in {"human", "json", "json-legacy", "sarif"}:
                    raise SchemaError(f"'output' must be a valid format, got {value!r}")
                out.output = str(value)
            elif key == "jobs":
                if not isinstance(value, int) or value < 0:
                    raise SchemaError("'jobs' must be a non-negative integer (0 = auto)")
                out.jobs = value
            elif key == "baseline":
                if not isinstance(value, str):
                    raise SchemaError("'baseline' must be a string path")
                out.baseline = value
            elif key == "severity_remap":
                if not isinstance(value, dict):
                    raise SchemaError("'severity_remap' must be a table of rule-id -> severity")
                for rid, sev in value.items():
                    _expect_severity(sev, f"severity_remap.{rid}")
                out.severity_remap = dict(value)
            elif key == "rules":
                if not isinstance(value, dict):
                    raise SchemaError("'[rules]' must be a table")
                for rid, rdata in value.items():
                    if rid == "enable":
                        out.enable = _expect_str_list(rdata, "rules.enable")
                    elif rid == "disable":
                        out.disable = _expect_str_list(rdata, "rules.disable")
                    elif isinstance(rdata, dict):
                        out.rules[rid] = RuleSettings.from_dict(rid, rdata)
                    else:
                        raise SchemaError(f"'[rules.{rid}]' must be a table")
            elif key == "overrides":
                if not isinstance(value, list):
                    raise SchemaError("'overrides' must be an array of tables")
                out.overrides = [RuleOverride.from_dict(o) for o in value]
            elif key not in known:
                raise SchemaError(f"unknown key {key!r}")
        return out
