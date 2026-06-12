# SPDX-License-Identifier: Apache-2.0
"""Tests for CG-SEC-002: Hardcoded secret."""

from __future__ import annotations

from codeguard.engine.runner import AnalysisRunner
from tests.conftest import load_fixture

RULE_ID = "CG-SEC-002"
RUNNER = AnalysisRunner(rule_ids=[RULE_ID])


def active_findings(source: str) -> list:
    return [f for f in RUNNER.run(source, filename="test.py") if not f.suppressed]


class TestCGSEC002Vulnerable:
    def test_password_literal(self) -> None:
        src = 'password = "hunter2"\n'
        assert len(active_findings(src)) >= 1

    def test_api_key_literal(self) -> None:
        src = 'api_key = "sk-abc123"\n'
        assert len(active_findings(src)) >= 1

    def test_token_literal(self) -> None:
        src = 'auth_token = "Bearer abc123"\n'
        assert len(active_findings(src)) >= 1

    def test_secret_literal(self) -> None:
        src = 'client_secret = "mysecretvalue"\n'
        assert len(active_findings(src)) >= 1

    def test_annotated_assignment(self) -> None:
        src = 'db_password: str = "postgres_pass"\n'
        assert len(active_findings(src)) >= 1

    def test_vulnerable_fixture(self) -> None:
        src = load_fixture("security", "cg_sec_002", "vulnerable")
        findings = active_findings(src)
        assert len(findings) >= 1, "Vulnerable fixture produced no findings"
        assert all(f.rule_id == RULE_ID for f in findings)


class TestCGSEC002Safe:
    def test_env_var_lookup(self) -> None:
        src = 'import os\npassword = os.environ["DB_PASSWORD"]\n'
        assert active_findings(src) == []

    def test_non_secret_variable_name(self) -> None:
        src = 'greeting = "hello world"\n'
        assert active_findings(src) == []

    def test_empty_string_default(self) -> None:
        # Empty string is not a secret
        src = 'password = ""\n'
        # Empty string has length 0 — below _MIN_SECRET_LEN
        # Safe, should not trigger
        assert active_findings(src) == []

    def test_safe_fixture(self) -> None:
        src = load_fixture("security", "cg_sec_002", "safe")
        findings = active_findings(src)
        assert findings == [], f"Safe fixture produced unexpected findings: {findings}"
