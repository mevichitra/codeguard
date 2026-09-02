# SPDX-License-Identifier: Apache-2.0
"""Tests for the local Markdown dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from click.testing import CliRunner

from codeguard.cli.main import cli
from codeguard.dashboard import render_dashboard, write_dashboard
from codeguard.engine.finding import Category, Finding, Location, Severity


def _finding(path: Path) -> Finding:
    return Finding(
        rule_id="CG-SEC-002",
        title="Hardcoded secret",
        description="A secret is embedded in source.",
        severity=Severity.HIGH,
        category=Category.SECURITY,
        location=Location(file=str(path), line=2, col=1),
        fix_suggestion="Load it from the environment.",
    )


def test_render_dashboard_contains_summary_and_links(tmp_path: Path) -> None:
    source = tmp_path / "app.py"
    report = render_dashboard(
        [_finding(source)],
        tmp_path,
        generated_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
    )

    assert "# 🛡️ CodeGuard Dashboard" in report
    assert "| **1** | 0 | 0 |" in report
    assert "app.py:2:1" in report
    assert "CG-SEC-002" in report
    assert "2026-09-01 12:00:00 UTC" in report


def test_write_dashboard_uses_explicit_output(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    written = write_dashboard([_finding(tmp_path / "app.py")], tmp_path, output=target)

    assert written == target
    assert target.is_file()


def test_dashboard_cli_generates_report(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "bad.py").write_text('password = "secret-value"\n', encoding="utf-8")
    output = tmp_path / "dashboard.md"

    result = CliRunner().invoke(cli, ["dashboard", str(tmp_path), "--output", str(output)])

    assert result.exit_code == 0
    assert result.output.strip() == str(output)
    assert "Hardcoded secret" in output.read_text(encoding="utf-8")
