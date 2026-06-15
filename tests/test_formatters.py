# SPDX-License-Identifier: Apache-2.0
"""Tests for CLI formatters."""

from __future__ import annotations

from pathlib import Path

from codeguard.cli.formatters import format_human
from codeguard.engine.finding import Category, Finding, Location, Severity


def _finding(file_path: Path, *, line: int, col: int) -> Finding:
    return Finding(
        rule_id="CG-TEST-001",
        title="Test finding",
        description="Test description",
        severity=Severity.LOW,
        category=Category.QUALITY,
        location=Location(file=str(file_path), line=line, col=col),
    )


def test_format_human_source_preview_allows_square_brackets(tmp_path: Path) -> None:
    source_file = tmp_path / "sample.py"
    source_file.write_text("value = items[0]\n", encoding="utf-8")

    line = 1
    col = 14
    output = format_human([_finding(source_file, line=line, col=col)])

    lines = output.splitlines()
    source_line_index = lines.index("     1 | value = items[0]")
    gutter = f"{line:>4}"
    assert lines[source_line_index + 1] == f"  {' ' * (len(gutter) + 3 + col)}^"


def test_format_human_pointer_aligns_for_large_line_numbers(tmp_path: Path) -> None:
    source_file = tmp_path / "sample.py"
    source_file.write_text(("\n" * 9999) + "token = 1\n", encoding="utf-8")

    line = 10000
    col = 2
    output = format_human([_finding(source_file, line=line, col=col)])

    lines = output.splitlines()
    source_line_index = lines.index("  10000 | token = 1")
    gutter = f"{line:>4}"
    assert lines[source_line_index + 1] == f"  {' ' * (len(gutter) + 3 + col)}^"
