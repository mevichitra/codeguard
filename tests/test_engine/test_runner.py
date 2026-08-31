# SPDX-License-Identifier: Apache-2.0
"""Tests for AnalysisRunner: suppression, syntax errors, multi-file scanning."""

from __future__ import annotations

import textwrap
import warnings
from pathlib import Path

import pytest

from codeguard.engine.registry import RuleRegistry
from codeguard.engine.runner import AnalysisRunner


class TestAnalysisRunner:
    def test_run_returns_list(self) -> None:
        # Use real rules via the module-level REGISTRY (loaded in conftest)
        runner = AnalysisRunner()
        findings = runner.run("x = 1\n")
        assert isinstance(findings, list)

    def test_syntax_error_raises(self) -> None:
        runner = AnalysisRunner()
        with pytest.raises(SyntaxError):
            runner.run("def foo(\n")

    def test_run_file_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.py"
        bad.write_text("def foo(\n", encoding="utf-8")
        runner = AnalysisRunner()
        with warnings.catch_warnings(record=True):
            findings = runner.run_file(bad)
        assert findings == []

    def test_suppression_marks_finding(self) -> None:
        # A rule that always fires on any source
        from codeguard.engine.finding import Category, Finding, Location, Severity
        from codeguard.engine.rule import AstRule

        class AlwaysFires(AstRule):
            id = "CG-TEST-999"
            title = "Always fires"
            description = "Test rule"
            severity = Severity.HIGH
            category = Category.SECURITY

            def check_ast(self, tree, source, filename):  # type: ignore[override]
                return [
                    Finding(
                        rule_id=self.id,
                        title=self.title,
                        description=self.description,
                        severity=self.severity,
                        category=self.category,
                        location=Location(file=filename, line=1, col=1),
                    )
                ]

        registry = RuleRegistry()
        registry.register(AlwaysFires())
        runner = AnalysisRunner(registry=registry)

        src = "x = 1  # codeguard: ignore[CG-TEST-999]\n"
        findings = runner.run(src, filename="test.py")
        assert len(findings) == 1
        assert findings[0].suppressed is True

    def test_file_disable_suppresses_findings(self) -> None:
        from codeguard.engine.finding import Category, Finding, Location, Severity
        from codeguard.engine.rule import AstRule

        class AlwaysFires(AstRule):
            id = "CG-TEST-888"
            title = "Always fires"
            description = "Test rule"
            severity = Severity.HIGH
            category = Category.SECURITY

            def check_ast(self, tree, source, filename):  # type: ignore[override]
                return [
                    Finding(
                        rule_id=self.id,
                        title=self.title,
                        description=self.description,
                        severity=self.severity,
                        category=self.category,
                        location=Location(file=filename, line=2, col=1),
                    )
                ]

        registry = RuleRegistry()
        registry.register(AlwaysFires())
        runner = AnalysisRunner(registry=registry)

        src = "# codeguard: disable[CG-TEST-888]\nx = 1\n"
        findings = runner.run(src, filename="test.py")
        assert len(findings) == 1
        assert findings[0].suppressed is True

    def test_rule_id_filter(self) -> None:
        """Only the requested rules should run."""
        runner = AnalysisRunner(rule_ids=["CG-SEC-001"])
        # This is a safe SQL query — should produce no CG-SEC-001 findings
        src = 'cursor.execute("SELECT 1")\n'
        findings = runner.run(src)
        assert all(f.rule_id == "CG-SEC-001" for f in findings)

    def test_run_path_directory(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.py"
        f1.write_text("x = 1\n", encoding="utf-8")
        runner = AnalysisRunner()
        findings = runner.run_path(tmp_path)
        assert isinstance(findings, list)

    def test_parallel_matches_sequential(self, tmp_path: Path) -> None:
        for i in range(4):
            (tmp_path / f"m{i}.py").write_text(
                f'password{i} = "s"\ncur.execute(f"SELECT {{x{i}}}")\n', encoding="utf-8"
            )
        files = sorted(tmp_path.glob("*.py"))
        runner = AnalysisRunner()
        seq = runner.run_files(files, jobs=1)
        par = runner.run_files(files, jobs=2)
        assert [(f.location.file, f.location.line, f.rule_id) for f in seq] == [
            (f.location.file, f.location.line, f.rule_id) for f in par
        ]
        assert [f.fingerprint for f in seq] == [f.fingerprint for f in par]

    def test_findings_sorted_by_line(self) -> None:
        """Runner must return findings sorted by (file, line, rule_id)."""
        import codeguard.rules  # noqa: F401 — ensure rules loaded

        runner = AnalysisRunner()
        src = textwrap.dedent("""\
            password = "secret"
            x = 1
            cursor.execute(f"SELECT {x}")
        """)
        findings = runner.run(src, filename="test.py")
        lines = [f.location.line for f in findings if not f.suppressed]
        assert lines == sorted(lines)
