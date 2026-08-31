# SPDX-License-Identifier: Apache-2.0
"""Tests for CodeGuard CLI scanning options and validation."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from codeguard.cli.main import EXIT_ERROR, EXIT_FINDINGS, cli


def test_scan_invalid_rule(tmp_path: Path) -> None:
    """Invoking CLI scan with an invalid rule ID must exit with an error code."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", str(test_file), "--rule", "CG-INVALID-001"])

    assert result.exit_code == EXIT_ERROR
    assert "Error: Invalid rule ID(s) specified: CG-INVALID-001" in result.output


def test_scan_valid_rule(tmp_path: Path) -> None:
    """Invoking CLI scan with a valid rule ID runs scan successfully."""
    test_file = tmp_path / "test.py"
    test_file.write_text("password = 'secret'\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", str(test_file), "--rule", "CG-SEC-002"])

    assert result.exit_code == EXIT_FINDINGS
    assert "CG-SEC-002" in result.output
    assert "Hardcoded secret" in result.output


def test_scan_multiple_invalid_rules(tmp_path: Path) -> None:
    """Invoking CLI scan with multiple invalid rule IDs lists all of them in the error."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["scan", str(test_file), "--rule", "CG-INVALID-001", "--rule", "CG-INVALID-002"],
    )

    assert result.exit_code == EXIT_ERROR
    assert "Error: Invalid rule ID(s) specified: CG-INVALID-001, CG-INVALID-002" in result.output


def test_scan_exclude_skips_matching_files(tmp_path: Path) -> None:
    """CLI --exclude should prevent findings from excluded files."""
    safe_file = tmp_path / "safe.py"
    vulnerable_file = tmp_path / "ignored.py"
    safe_file.write_text("x = 1\n", encoding="utf-8")
    vulnerable_file.write_text("password = 'secret'\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["scan", str(tmp_path), "--rule", "CG-SEC-002", "--exclude", "ignored.py"],
    )

    assert result.exit_code == 0
    assert "CG-SEC-002" not in result.output


def test_scan_exclude_is_repeatable(tmp_path: Path) -> None:
    """CLI should support multiple --exclude options."""
    keep_file = tmp_path / "keep.py"
    ignored_a = tmp_path / "a.py"
    nested_dir = tmp_path / "ignored"
    ignored_b = nested_dir / "b.py"
    nested_dir.mkdir()

    keep_file.write_text("x = 1\n", encoding="utf-8")
    ignored_a.write_text("password = 'secret'\n", encoding="utf-8")
    ignored_b.write_text("password = 'secret'\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "scan",
            str(tmp_path),
            "--rule",
            "CG-SEC-002",
            "--exclude",
            "a.py",
            "--exclude",
            "ignored/**",
        ],
    )

    assert result.exit_code == 0
    assert "CG-SEC-002" not in result.output
