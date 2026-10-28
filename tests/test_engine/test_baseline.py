# SPDX-License-Identifier: Apache-2.0
"""Tests for baseline files (schema 2, with schema-1 files still loading)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codeguard.engine.baseline import Baseline, apply_baseline
from codeguard.engine.finding import Category, Finding, Location, Severity


def _f(rule_id: str, fp: str, line: int = 1, file: str = "a.py") -> Finding:
    return Finding(
        rule_id=rule_id,
        title="t",
        description="d",
        severity=Severity.HIGH,
        category=Category.SECURITY,
        location=Location(file=file, line=line, col=1),
        fingerprint=fp,
    )


def test_from_findings_and_contains() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa"), _f("CG-SEC-002", "bbb")])
    assert "aaa" in b and "bbb" in b
    assert len(b) == 2


def test_findings_without_fingerprint_or_identity_are_skipped() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "")])
    assert len(b) == 0


def test_roundtrip(tmp_path: Path) -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa")], tool_version="9.9.9", commit="c0ffee")
    path = tmp_path / "bl.json"
    b.save(path)
    loaded = Baseline.load(path)
    assert "aaa" in loaded
    assert loaded.tool_version == "9.9.9"
    assert loaded.commit == "c0ffee"
    data = json.loads(path.read_text())
    assert data["version"] == 2 and data["scheme"] == "codeguard/v2"
    assert data["findings"][0]["keys"] == {"v1": "aaa"}


def test_schema_one_file_loads_and_matches_on_v1(tmp_path: Path) -> None:
    path = tmp_path / "old.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "fingerprints": {
                    "aaa": {"rule_id": "CG-SEC-001", "file": "a.py", "first_seen": "2024-01-01"}
                },
            }
        ),
        encoding="utf-8",
    )
    b = Baseline.load(path)
    assert b.schema_version == 1 and len(b) == 1 and "aaa" in b
    assert b.records[0].first_seen == "2024-01-01"
    out = apply_baseline([_f("CG-SEC-001", "aaa"), _f("CG-SEC-001", "ccc")], b)
    assert [f.baselined for f in out] == [True, False]
    assert out[0].match is not None and out[0].match.pass_name == "v1"
    assert out[1].match is not None and out[1].match.status == "new"


def test_load_rejects_junk(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        Baseline.load(p)
    p.write_text('{"findings": [{"rule": 1}]}', encoding="utf-8")
    with pytest.raises(ValueError):
        Baseline.load(p)


def test_apply_marks_baselined() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa")])
    findings = [_f("CG-SEC-001", "aaa"), _f("CG-SEC-002", "new")]
    out = apply_baseline(findings, b)
    assert out[0].baselined is True
    assert out[1].baselined is False


def test_one_record_hides_one_finding() -> None:
    # Set membership is gone: two findings with the same key need two records.
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa", line=1)])
    out = apply_baseline([_f("CG-SEC-001", "aaa", line=1), _f("CG-SEC-001", "aaa", line=5)], b)
    assert [f.baselined for f in out] == [True, False]


def test_updated_with_keeps_first_seen_and_follows() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa", line=1)])
    original_seen = b.records[0].first_seen
    b2, followed, added = b.update([_f("CG-SEC-001", "aaa", line=9), _f("CG-SEC-002", "bbb")])
    assert (followed, added) == (1, 1)
    assert sorted(r.v1 for r in b2.records) == ["aaa", "bbb"]
    moved = next(r for r in b2.records if r.v1 == "aaa")
    assert moved.first_seen == original_seen and moved.line == 9


def test_updated_with_can_leave_new_findings_out() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa")])
    b2 = b.updated_with([_f("CG-SEC-001", "aaa"), _f("CG-SEC-002", "bbb")], add_new=False)
    assert [r.v1 for r in b2.records] == ["aaa"]


def test_pruned_drops_dead_entries() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa"), _f("CG-SEC-002", "bbb")])
    assert {r.v1 for r in b.pruned([_f("CG-SEC-001", "aaa")]).records} == {"aaa"}
    assert {r.v1 for r in b.pruned({"bbb"}).records} == {"bbb"}


def test_fingerprints_view_is_the_schema_one_shape() -> None:
    b = Baseline.from_findings([_f("CG-SEC-001", "aaa")])
    assert b.fingerprints["aaa"]["rule_id"] == "CG-SEC-001"
