# SPDX-License-Identifier: Apache-2.0
"""Tests for baseline files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codeguard.engine.baseline import Baseline, apply_baseline
from codeguard.engine.finding import Category, Finding, Location, Severity


def _f(rule_id: str, fp: str, line: int = 1) -> Finding:
    return Finding(
        rule_id=rule_id,
        title="t",
        description="d",
        severity=Severity.HIGH,
        category=Category.SECURITY,
        location=Location(file="a.py", line=line, col=1),
        fingerprint=fp,
    )


def test_from_findings_and_contains() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa"), _f("CG-SEC-002", "bbb")])
    assert "aaa" in b and "bbb" in b
    assert len(b) == 2


def test_findings_without_fingerprint_are_skipped() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "")])
    assert len(b) == 0


def test_roundtrip(tmp_path: Path) -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa")], tool_version="9.9.9")
    path = tmp_path / "bl.json"
    b.save(path)
    loaded = Baseline.load(path)
    assert "aaa" in loaded
    assert loaded.tool_version == "9.9.9"
    assert json.loads(path.read_text())["version"] == 1


def test_load_rejects_junk(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        Baseline.load(p)


def test_apply_marks_baselined() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa")])
    findings = [_f("CG-SEC-001", "aaa"), _f("CG-SEC-002", "new")]
    out = apply_baseline(findings, b)
    assert out[0].baselined is True
    assert out[1].baselined is False


def test_updated_with_keeps_first_seen() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa")])
    original_seen = b.fingerprints["aaa"]["first_seen"]
    b2 = b.updated_with([_f("CG-SEC-001", "aaa"), _f("CG-SEC-002", "bbb")])
    assert set(b2.fingerprints) == {"aaa", "bbb"}
    assert b2.fingerprints["aaa"]["first_seen"] == original_seen


def test_pruned_drops_dead_entries() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa"), _f("CG-SEC-002", "bbb")])
    pruned = b.pruned({"aaa"})
    assert set(pruned.fingerprints) == {"aaa"}
