# SPDX-License-Identifier: Apache-2.0
"""Tests for AnalysisRunner: suppression, syntax errors, multi-file scanning."""

from __future__ import annotations

import textwrap
import warnings
from pathlib import Path

import pytest

from codeguard.engine.finding import Category, Finding, Location, Severity
from codeguard.engine.registry import RuleRegistry
from codeguard.engine.rule import AstRule
from codeguard.engine.runner import AnalysisRunner, _parse_file_disables, _parse_suppressions


def _build_per_file_runner(exclude: list[str] | None = None) -> AnalysisRunner:
    class PerFileRule(AstRule):
        id = "CG-TEST-100"
        title = "Per-file marker"
        description = "Emits one finding for each scanned file."
        severity = Severity.LOW
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
    registry.register(PerFileRule())
    return AnalysisRunner(registry=registry, exclude=exclude)


class TestParseSuppressions:
    def test_single_rule(self) -> None:
        src = "x = 1  # codeguard: ignore[CG-SEC-001]\n"
        result = _parse_suppressions(src)
        assert result == {1: {"CG-SEC-001"}}

    def test_multiple_rules(self) -> None:
        src = "x = 1  # codeguard: ignore[CG-SEC-001, CG-SEC-002]\n"
        result = _parse_suppressions(src)
        assert result == {1: {"CG-SEC-001", "CG-SEC-002"}}

    def test_no_suppressions(self) -> None:
        src = "x = 1\ny = 2\n"
        assert _parse_suppressions(src) == {}

    def test_correct_line_number(self) -> None:
        src = "a = 1\nb = 2  # codeguard: ignore[CG-SEC-003]\nc = 3\n"
        result = _parse_suppressions(src)
        assert 2 in result
        assert "CG-SEC-003" in result[2]


class TestParseFileDisables:
    def test_single_disable(self) -> None:
        src = "# codeguard: disable[CG-SEC-001]\nx = 1\n"
        assert _parse_file_disables(src) == {"CG-SEC-001"}

    def test_multiple_disables_in_one_line(self) -> None:
        src = "# codeguard: disable[CG-SEC-001, CG-SEC-002]\nx = 1\n"
        assert _parse_file_disables(src) == {"CG-SEC-001", "CG-SEC-002"}

    def test_multiple_disable_lines(self) -> None:
        src = textwrap.dedent("""\
            # codeguard: disable[CG-SEC-001]
            # codeguard: disable[CG-SEC-003]
            x = 1
        """)
        assert _parse_file_disables(src) == {"CG-SEC-001", "CG-SEC-003"}

    def test_no_disables(self) -> None:
        src = "x = 1\n"
        assert _parse_file_disables(src) == set()


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

    def test_run_path_excludes_single_file_pattern(self, tmp_path: Path) -> None:
        a_file = tmp_path / "a.py"
        b_file = tmp_path / "b.py"
        a_file.write_text("x = 1\n", encoding="utf-8")
        b_file.write_text("x = 2\n", encoding="utf-8")

        runner = _build_per_file_runner(exclude=["b.py"])
        findings = runner.run_path(tmp_path)
        scanned_files = sorted({Path(f.location.file).name for f in findings})

        assert scanned_files == ["a.py"]

    def test_run_path_excludes_directory_name_pattern(self, tmp_path: Path) -> None:
        kept_file = tmp_path / "app.py"
        ignored_dir = tmp_path / "ignored"
        ignored_file = ignored_dir / "skip.py"
        ignored_dir.mkdir()
        kept_file.write_text("x = 1\n", encoding="utf-8")
        ignored_file.write_text("x = 2\n", encoding="utf-8")

        runner = _build_per_file_runner(exclude=["ignored"])
        findings = runner.run_path(tmp_path)
        scanned_files = sorted(
            Path(f.location.file).relative_to(tmp_path).as_posix() for f in findings
        )

        assert scanned_files == ["app.py"]

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
