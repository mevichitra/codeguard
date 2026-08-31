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
    assert "Error: unknown rule ID(s): CG-INVALID-001" in result.output


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
    assert "Error: unknown rule ID(s): CG-INVALID-001, CG-INVALID-002" in result.output
