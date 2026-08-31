# SPDX-License-Identifier: Apache-2.0
"""Tests for CG-SEC-001: SQL query built with string formatting."""

from __future__ import annotations

from codeguard.engine.runner import AnalysisRunner
from tests.conftest import load_fixture

RULE_ID = "CG-SEC-001"
RUNNER = AnalysisRunner(rule_ids=[RULE_ID])


def active_findings(source: str) -> list:
    return [f for f in RUNNER.run(source, filename="test.py") if not f.suppressed]


class TestCGSEC001Vulnerable:
    def test_fstring_in_execute(self) -> None:
        src = 'cursor.execute(f"SELECT * FROM users WHERE id = {uid}")\n'
        findings = active_findings(src)
        assert len(findings) >= 1
        assert findings[0].rule_id == RULE_ID

    def test_percent_format_in_execute(self) -> None:
        src = 'cursor.execute("SELECT * FROM users WHERE id = %s" % uid)\n'
        findings = active_findings(src)
        assert len(findings) >= 1

    def test_dot_format_in_execute(self) -> None:
        src = 'cursor.execute("SELECT * FROM {} WHERE active = 1".format(table))\n'
        findings = active_findings(src)
        assert len(findings) >= 1

    def test_concat_in_execute(self) -> None:
        src = 'cursor.execute("DELETE FROM " + table + " WHERE id = 1")\n'
        findings = active_findings(src)
        assert len(findings) >= 1

    def test_executemany_flagged(self) -> None:
        src = 'cursor.executemany(f"INSERT INTO {table} VALUES (?)", data)\n'
        findings = active_findings(src)
        assert len(findings) >= 1

    def test_vulnerable_fixture(self) -> None:
        src = load_fixture("python", "security", "cg_sec_001", "vulnerable")
        findings = active_findings(src)
        assert len(findings) >= 1, "Vulnerable fixture produced no findings"
        assert all(f.rule_id == RULE_ID for f in findings)


class TestCGSEC001Safe:
    def test_parameterized_question_mark(self) -> None:
        src = 'cursor.execute("SELECT * FROM users WHERE id = ?", (uid,))\n'
        assert active_findings(src) == []

    def test_parameterized_percent_s(self) -> None:
        src = 'cursor.execute("SELECT * FROM users WHERE id = %s", (uid,))\n'
        assert active_findings(src) == []

    def test_literal_query_no_args(self) -> None:
        src = 'cursor.execute("SELECT * FROM users WHERE active = 1")\n'
        assert active_findings(src) == []

    def test_multipart_literal_concat(self) -> None:
        # Left-associative concat of string literals is static, not dynamic (issue #5)
        src = 'cursor.execute("SELECT " + " * " + " FROM users")\n'
        assert active_findings(src) == []

    def test_safe_fixture(self) -> None:
        src = load_fixture("python", "security", "cg_sec_001", "safe")
        findings = active_findings(src)
        assert findings == [], f"Safe fixture produced unexpected findings: {findings}"


class TestCGSEC001Suppression:
    def test_suppressed_not_in_active(self) -> None:
        src = 'cursor.execute(f"SELECT {uid}")  # codeguard: ignore[CG-SEC-001]\n'
        findings = RUNNER.run(src, filename="test.py")
        assert any(f.suppressed for f in findings)
        assert not any(f for f in findings if not f.suppressed)
