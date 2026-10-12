# SPDX-License-Identifier: Apache-2.0
"""Tests for the Python taint rules CG-SEC-010..014 and their interplay with pattern rules."""

from __future__ import annotations

import pytest

from codeguard.engine.runner import AnalysisRunner
from tests.conftest import load_fixture

EXPECTED_VULNERABLE = {
    "cg_sec_010": ("CG-SEC-010", 2),
    "cg_sec_011": ("CG-SEC-011", 2),
    "cg_sec_012": ("CG-SEC-012", 1),
    "cg_sec_013": ("CG-SEC-013", 2),
    "cg_sec_014": ("CG-SEC-014", 1),
}


def _ids(src: str, rule_ids: list[str] | None = None) -> list[str]:
    runner = AnalysisRunner(rule_ids=rule_ids)
    return [f.rule_id for f in runner.run(src, filename="app.py") if not f.suppressed]


@pytest.mark.parametrize("fixture", sorted(EXPECTED_VULNERABLE))
def test_vulnerable_fixture(fixture: str) -> None:
    rule_id, count = EXPECTED_VULNERABLE[fixture]
    src = load_fixture("python", "security", fixture, "vulnerable")
    assert _ids(src, [rule_id]) == [rule_id] * count


@pytest.mark.parametrize("fixture", sorted(EXPECTED_VULNERABLE))
def test_safe_fixture(fixture: str) -> None:
    rule_id, _ = EXPECTED_VULNERABLE[fixture]
    assert _ids(load_fixture("python", "security", fixture, "safe"), [rule_id]) == []


def test_taint_replaces_pattern_finding_on_same_line() -> None:
    src = "import os\nfrom flask import request\ncmd = request.args['c']\nos.system(cmd)\n"
    assert _ids(src, ["CG-SEC-005", "CG-SEC-011"]) == ["CG-SEC-011"]


def test_pattern_finding_kept_without_taint() -> None:
    src = "import os\ndef f(cmd):\n    os.system(cmd)\n"
    assert _ids(src, ["CG-SEC-005", "CG-SEC-011"]) == ["CG-SEC-005"]


def test_inline_tainted_eval_reported_once() -> None:
    src = "from flask import request\neval(request.args['e'] + '1')\n"
    assert _ids(src, ["CG-SEC-003", "CG-SEC-012"]) == ["CG-SEC-012"]


def test_finding_carries_taint_path() -> None:
    src = load_fixture("python", "security", "cg_sec_011", "vulnerable")
    finding = AnalysisRunner(rule_ids=["CG-SEC-011"]).run(src, filename="app.py")[0]
    messages = [r.message for r in finding.related]
    assert messages[0] == "Untrusted input: flask request.form"
    assert messages[-1] == 'Flows through: cmd = "ping -c 1 " + host'
    assert "flask request.form (line 9) via 2 assignments" in finding.description
    assert finding.confidence == pytest.approx(0.85)
    assert finding.to_dict()["related"][0]["line"] == 9


def test_local_source_lower_confidence_and_path_rule_ignores_it() -> None:
    src = "import os, sys\nos.system(sys.argv[1])\nopen(sys.argv[2])\n"
    findings = AnalysisRunner(rule_ids=["CG-SEC-011", "CG-SEC-013"]).run(src, filename="cli.py")
    assert [f.rule_id for f in findings] == ["CG-SEC-011"]
    assert findings[0].confidence == pytest.approx(0.6)


def test_suppression_applies_to_taint_rule() -> None:
    src = (
        "import os\nfrom flask import request\n"
        "os.system(request.args['c'])  # codeguard: ignore[CG-SEC-011] reason: admin-only\n"
    )
    findings = AnalysisRunner(rule_ids=["CG-SEC-005", "CG-SEC-011"]).run(src, filename="a.py")
    assert [(f.rule_id, f.suppressed) for f in findings] == [("CG-SEC-011", True)]


class TestSqlPatternHops:
    """CG-SEC-001 follows one local assignment and recognises local constants."""

    def test_query_built_in_variable(self) -> None:
        src = 'def f(cur, uid):\n    q = f"SELECT {uid}"\n    cur.execute(q)\n'
        findings = AnalysisRunner(rule_ids=["CG-SEC-001"]).run(src, filename="a.py")
        assert len(findings) == 1
        assert findings[0].related[0].location.line == 2

    def test_variable_reassigned_to_constant(self) -> None:
        src = 'def f(cur, uid):\n    q = f"SELECT {uid}"\n    q = "SELECT 1"\n    cur.execute(q)\n'
        assert _ids(src, ["CG-SEC-001"]) == []

    def test_concat_with_local_constant(self) -> None:
        src = 'def f(cur):\n    t = "users"\n    cur.execute("SELECT * FROM " + t)\n'
        assert _ids(src, ["CG-SEC-001"]) == []

    def test_concat_with_parameter_still_flagged(self) -> None:
        src = 'def f(cur, t):\n    cur.execute("SELECT * FROM " + t)\n'
        assert _ids(src, ["CG-SEC-001"]) == ["CG-SEC-001"]

    def test_other_scope_assignment_ignored(self) -> None:
        src = 'q = f"SELECT {x}"\ndef f(cur, q):\n    cur.execute(q)\n'
        assert _ids(src, ["CG-SEC-001"]) == []
