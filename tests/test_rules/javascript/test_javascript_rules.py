# SPDX-License-Identifier: Apache-2.0
"""Tests for the JavaScript / TypeScript security rules (CG-SEC-101..106)."""

from __future__ import annotations

import pytest

from codeguard.engine.runner import AnalysisRunner
from tests.conftest import fixture_path, load_fixture

RUNNER = AnalysisRunner()


def _findings(source: str, filename: str, rule_id: str) -> list:
    return [
        f
        for f in RUNNER.run(source, filename=filename)
        if f.rule_id == rule_id and not f.suppressed
    ]


def _fixture_findings(rule_id: str, name: str) -> list:
    rule_dir = rule_id.lower().replace("-", "_")
    src = load_fixture("javascript", "security", rule_dir, name)
    path = fixture_path("javascript", "security", rule_dir, name)
    return _findings(src, str(path), rule_id)


RULES = ["CG-SEC-101", "CG-SEC-102", "CG-SEC-103", "CG-SEC-104", "CG-SEC-105", "CG-SEC-106"]


@pytest.mark.parametrize("rule_id", RULES)
def test_vulnerable_fixture_triggers(rule_id: str) -> None:
    findings = _fixture_findings(rule_id, "vulnerable")
    assert len(findings) >= 1, f"{rule_id} vulnerable fixture produced no findings"


@pytest.mark.parametrize("rule_id", RULES)
def test_safe_fixture_clean(rule_id: str) -> None:
    assert _fixture_findings(rule_id, "safe") == []


class TestCGSEC101:
    def test_eval_dynamic(self) -> None:
        assert _findings("eval(userInput);\n", "a.js", "CG-SEC-101")

    def test_eval_literal_ok(self) -> None:
        assert not _findings('eval("1+1");\n', "a.js", "CG-SEC-101")

    def test_new_function_dynamic(self) -> None:
        assert _findings('new Function("return " + x);\n', "a.js", "CG-SEC-101")

    def test_string_timer(self) -> None:
        assert _findings('setInterval("tick()", 10);\n', "a.js", "CG-SEC-101")

    def test_function_timer_ok(self) -> None:
        assert not _findings("setTimeout(() => tick(), 10);\n", "a.js", "CG-SEC-101")

    def test_typescript_too(self) -> None:
        assert _findings("const x: string = eval(y);\n", "a.ts", "CG-SEC-101")


class TestCGSEC102:
    def test_exec_concat(self) -> None:
        assert _findings('cp.exec("git " + b);\n', "a.js", "CG-SEC-102")

    def test_execsync_var(self) -> None:
        assert _findings("cp.execSync(cmd);\n", "a.js", "CG-SEC-102")

    def test_exec_literal_ok(self) -> None:
        assert not _findings('cp.exec("git status");\n', "a.js", "CG-SEC-102")

    def test_execfile_ok(self) -> None:
        assert not _findings('cp.execFile("git", [b]);\n', "a.js", "CG-SEC-102")


class TestCGSEC103:
    def test_inner_html(self) -> None:
        assert _findings("el.innerHTML = x;\n", "a.js", "CG-SEC-103")

    def test_inner_html_literal_ok(self) -> None:
        assert not _findings('el.innerHTML = "<p>hi</p>";\n', "a.js", "CG-SEC-103")

    def test_text_content_ok(self) -> None:
        assert not _findings("el.textContent = x;\n", "a.js", "CG-SEC-103")

    def test_document_write(self) -> None:
        assert _findings("document.write(x);\n", "a.js", "CG-SEC-103")


class TestCGSEC105:
    def test_secret_var(self) -> None:
        assert _findings('const apiKey = "sk-abc123";\n', "a.js", "CG-SEC-105")

    def test_env_ok(self) -> None:
        assert not _findings("const apiKey = process.env.KEY;\n", "a.js", "CG-SEC-105")

    def test_non_secret_name_ok(self) -> None:
        assert not _findings('const label = "just text";\n', "a.js", "CG-SEC-105")


class TestCGSEC106:
    def test_token_uses_math_random(self) -> None:
        assert _findings("const token = Math.random();\n", "a.js", "CG-SEC-106")

    def test_plain_math_random_ok(self) -> None:
        assert not _findings("const delay = Math.random() * 100;\n", "a.js", "CG-SEC-106")
