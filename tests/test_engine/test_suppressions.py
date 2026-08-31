# SPDX-License-Identifier: Apache-2.0
"""Tests for suppression parsing and the CG-META rules."""

from __future__ import annotations

from datetime import date

from codeguard.engine.runner import AnalysisRunner
from codeguard.engine.suppressions import SuppressionSet

RUNNER = AnalysisRunner()

SQL = 'cur.execute(f"SELECT {x}")'


def _run(src: str, *, now: date | None = None) -> list:
    return RUNNER.run(src, filename="m.py", now=now)


class TestParse:
    def test_inline_with_reason_and_until(self) -> None:
        s = SuppressionSet.parse(
            "x = 1  # codeguard: ignore[CG-SEC-001] reason: it is fine  until=2027-01-31\n"
        )
        supp = s.inline[1][0]
        assert supp.rule_ids == frozenset({"CG-SEC-001"})
        assert supp.reason == "it is fine"
        assert supp.until == date(2027, 1, 31)
        assert supp.file_level is False

    def test_file_level_and_disable_alias(self) -> None:
        s = SuppressionSet.parse(
            "# codeguard: ignore-file[CG-SEC-001] reason: a\n"
            "# codeguard: disable[CG-SEC-002] reason: b\n"
        )
        assert len(s.file_level) == 2
        assert all(x.file_level for x in s.file_level)

    def test_slash_comment(self) -> None:
        s = SuppressionSet.parse("const x = 1; // codeguard: ignore[CG-SEC-101] reason: ok\n")
        assert s.inline[1][0].rule_ids == frozenset({"CG-SEC-101"})

    def test_multiple_rule_ids(self) -> None:
        s = SuppressionSet.parse("x  # codeguard: ignore[CG-SEC-001, CG-SEC-002] reason: r\n")
        assert s.inline[1][0].rule_ids == frozenset({"CG-SEC-001", "CG-SEC-002"})

    def test_no_reason(self) -> None:
        s = SuppressionSet.parse("x  # codeguard: ignore[CG-SEC-001]\n")
        assert s.inline[1][0].reason is None


class TestOutcome:
    def test_active_suppresses(self) -> None:
        findings = _run(f"{SQL}  # codeguard: ignore[CG-SEC-001] reason: r\n")
        sec = [f for f in findings if f.rule_id == "CG-SEC-001"]
        assert sec and sec[0].suppressed
        assert not [f for f in findings if f.rule_id.startswith("CG-META")]

    def test_missing_reason_raises_meta_001(self) -> None:
        findings = _run(f"{SQL}  # codeguard: ignore[CG-SEC-001]\n")
        assert [f for f in findings if f.rule_id == "CG-META-001" and not f.suppressed]
        assert [f for f in findings if f.rule_id == "CG-SEC-001" and f.suppressed]

    def test_expired_reactivates_and_raises_meta_002(self) -> None:
        src = f"{SQL}  # codeguard: ignore[CG-SEC-001] reason: r  until=2020-01-01\n"
        findings = _run(src, now=date(2026, 1, 1))
        assert [f for f in findings if f.rule_id == "CG-SEC-001" and not f.suppressed]
        assert [f for f in findings if f.rule_id == "CG-META-002" and not f.suppressed]

    def test_not_yet_expired_still_suppresses(self) -> None:
        src = f"{SQL}  # codeguard: ignore[CG-SEC-001] reason: r  until=2099-01-01\n"
        findings = _run(src, now=date(2026, 1, 1))
        assert [f for f in findings if f.rule_id == "CG-SEC-001" and f.suppressed]
        assert not [f for f in findings if f.rule_id == "CG-META-002"]

    def test_meta_can_be_self_suppressed(self) -> None:
        src = f"{SQL}  # codeguard: ignore[CG-SEC-001, CG-META-001]\n"
        findings = _run(src)
        meta = [f for f in findings if f.rule_id == "CG-META-001"]
        assert meta and meta[0].suppressed

    def test_meta_rules_disabled_via_filter(self) -> None:
        runner = AnalysisRunner(rule_ids=["CG-SEC-001"])
        findings = runner.run(f"{SQL}  # codeguard: ignore[CG-SEC-001]\n", filename="m.py")
        assert not [f for f in findings if f.rule_id.startswith("CG-META")]
