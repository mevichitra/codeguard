# SPDX-License-Identifier: Apache-2.0
"""Rule options, supersedes de-duplication, category and language filters."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pytest

from codeguard.analysis import active_rule_ids, discovery_config, validate_rule_options
from codeguard.config import ConfigError
from codeguard.config.schema import Config
from codeguard.engine.context import RuleContext
from codeguard.engine.discovery import discover
from codeguard.engine.finding import Category, Finding, Location, Severity
from codeguard.engine.registry import REGISTRY, RuleRegistry
from codeguard.engine.rule import Rule
from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.base import Language


class _OptionRule(Rule):
    id = "CG-TEST-OPT"
    title = "reports its option"
    description = "d"
    severity = Severity.LOW
    category = Category.QUALITY
    languages = frozenset({Language.PYTHON})
    default_options: ClassVar[dict[str, object]] = {"limit": 3, "label": "x"}
    seen: ClassVar[list[Any]] = []

    def analyze(self, ctx: RuleContext) -> list[Finding]:
        self.seen.append((ctx.option("limit"), ctx.option("label"), ctx.option("nope", 7)))
        return []


def _line_rule(rule_id: str, *, supersedes: frozenset[str] = frozenset()) -> Rule:
    class _R(Rule):
        id = rule_id
        title = rule_id
        description = "d"
        severity = Severity.HIGH
        category = Category.SECURITY
        languages = frozenset({Language.PYTHON})

        def analyze(self, ctx: RuleContext) -> list[Finding]:
            return [
                Finding(
                    self.id,
                    self.title,
                    "d",
                    self.severity,
                    self.category,
                    Location(ctx.filename, 1, 1),
                )
            ]

    _R.supersedes = supersedes
    return _R()


def test_options_default_and_override() -> None:
    reg = RuleRegistry()
    rule = _OptionRule()
    rule.seen.clear()
    reg.register(rule)
    AnalysisRunner(registry=reg).run("x = 1\n")
    AnalysisRunner(registry=reg, rule_options={"CG-TEST-OPT": {"limit": 9}}).run("x = 1\n")
    assert rule.seen == [(3, "x", 7), (9, "x", 7)]


def test_supersedes_drops_pattern_finding_on_same_line() -> None:
    reg = RuleRegistry()
    reg.register(_line_rule("CG-TEST-PAT"))
    reg.register(_line_rule("CG-TEST-TAINT", supersedes=frozenset({"CG-TEST-PAT"})))
    ids = [f.rule_id for f in AnalysisRunner(registry=reg).run("x = 1\n")]
    assert ids == ["CG-TEST-TAINT"]
    # Without the superseding rule active, the pattern rule still reports.
    ids = [f.rule_id for f in AnalysisRunner(registry=reg, rule_ids=["CG-TEST-PAT"]).run("x\n")]
    assert ids == ["CG-TEST-PAT"]


def test_schema_routes_unknown_keys_to_options() -> None:
    cfg = Config.from_dict({"rules": {"CG-SEC-001": {"severity": "low", "foo": 1}}})
    assert cfg.rules["CG-SEC-001"].options == {"foo": 1}


def test_validate_rule_options_rejects_unknown_option() -> None:
    cfg = Config.from_dict({"rules": {"CG-SEC-001": {"max_complexity": 3}}})
    with pytest.raises(ConfigError, match=r"unknown option rules\.CG-SEC-001\.max_complexity"):
        validate_rule_options(cfg)


def test_validate_rule_options_checks_type() -> None:
    rule = next((r for r in REGISTRY.all() if r.default_options), None)
    if rule is None:
        pytest.skip("no built-in rule declares options")
    name, default = next(iter(rule.default_options.items()))
    bad = "text" if not isinstance(default, str) else 5
    cfg = Config.from_dict({"rules": {rule.id: {name: bad}}})
    with pytest.raises(ConfigError, match="must be"):
        validate_rule_options(cfg)
    cfg = Config.from_dict({"rules": {rule.id: {name: default}}})
    validate_rule_options(cfg)


def test_category_filter_keeps_meta() -> None:
    ids = active_rule_ids(Config(), None, categories=["security"])
    assert "CG-SEC-001" in ids and "CG-META-001" in ids
    assert all(REGISTRY.get(i).category.value in ("security", "meta") for i in ids)  # type: ignore[union-attr]
    with pytest.raises(ConfigError):
        active_rule_ids(Config(), None, categories=["nonsense"])


def test_extra_disabled() -> None:
    assert "CG-SEC-001" not in active_rule_ids(Config(), None, extra_disabled=["CG-SEC-001"])


def test_languages_config_filters_discovery(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.js").write_text("let x = 1;\n")
    cfg = Config.from_dict({"languages": ["javascript"]})
    files = discover([tmp_path], discovery_config(cfg), root=tmp_path)
    assert [f.name for f in files] == ["b.js"]
