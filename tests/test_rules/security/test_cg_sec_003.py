# SPDX-License-Identifier: Apache-2.0
"""Tests for CG-SEC-003: eval() / exec() on dynamic input."""

from __future__ import annotations

from codeguard.engine.runner import AnalysisRunner
from tests.conftest import load_fixture

RULE_ID = "CG-SEC-003"
RUNNER = AnalysisRunner(rule_ids=[RULE_ID])


def active_findings(source: str) -> list:
    return [f for f in RUNNER.run(source, filename="test.py") if not f.suppressed]


class TestCGSEC003Vulnerable:
    def test_eval_variable(self) -> None:
        src = "eval(user_input)\n"
        assert len(active_findings(src)) >= 1

    def test_exec_variable(self) -> None:
        src = "exec(script)\n"
        assert len(active_findings(src)) >= 1

    def test_compile_variable(self) -> None:
        src = 'compile(code_str, "<string>", "exec")\n'
        assert len(active_findings(src)) >= 1

    def test_eval_method_call(self) -> None:
        src = "eval(request.get_data())\n"
        assert len(active_findings(src)) >= 1

    def test_vulnerable_fixture(self) -> None:
        src = load_fixture("security", "cg_sec_003", "vulnerable")
        findings = active_findings(src)
        assert len(findings) >= 1, "Vulnerable fixture produced no findings"
        assert all(f.rule_id == RULE_ID for f in findings)


class TestCGSEC003Safe:
    def test_eval_literal_string(self) -> None:
        # eval on a literal — not the dangerous case
        src = 'eval("1 + 1")\n'
        assert active_findings(src) == []

    def test_exec_literal_string(self) -> None:
        src = 'exec("pass")\n'
        assert active_findings(src) == []

    def test_safe_fixture(self) -> None:
        src = load_fixture("security", "cg_sec_003", "safe")
        findings = active_findings(src)
        assert findings == [], f"Safe fixture produced unexpected findings: {findings}"
