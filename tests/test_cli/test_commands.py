# SPDX-License-Identifier: Apache-2.0
"""Tests for list-rules, explain, validate, and init."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from codeguard.cli import commands
from codeguard.cli.main import cli


class TestListRules:
    def test_table(self) -> None:
        r = CliRunner().invoke(cli, ["list-rules"])
        assert r.exit_code == 0
        assert "CG-SEC-001" in r.output and "CG-SEC-005" in r.output

    def test_json(self) -> None:
        r = CliRunner().invoke(cli, ["list-rules", "--format", "json"])
        data = json.loads(r.output)
        assert {row["id"] for row in data} >= {"CG-SEC-001", "CG-SEC-101"}
        by_id = {row["id"]: row for row in data}
        assert by_id["CG-SEC-001"]["languages"] == ["python"]
        assert set(by_id["CG-SEC-101"]["languages"]) == {"javascript", "typescript"}

    def test_filter_language(self) -> None:
        r = CliRunner().invoke(cli, ["list-rules", "--language", "javascript", "--format", "json"])
        ids = {row["id"] for row in json.loads(r.output)}
        assert "CG-SEC-101" in ids
        assert "CG-SEC-001" not in ids  # python-only


class TestExplain:
    def test_known(self) -> None:
        r = CliRunner().invoke(cli, ["explain", "CG-SEC-001"])
        assert r.exit_code == 0
        assert "CWE-89" in r.output
        assert "rules/cg-sec-001/" in r.output

    def test_unknown(self) -> None:
        r = CliRunner().invoke(cli, ["explain", "CG-NOPE-999"])
        assert r.exit_code == 2


class TestValidate:
    def test_ok(self, tmp_path: Path) -> None:
        f = tmp_path / "codeguard.toml"
        f.write_text('[codeguard]\nfail_on = "high"\n', encoding="utf-8")
        r = CliRunner().invoke(cli, ["validate", "--config", str(f)])
        assert r.exit_code == 0
        assert "OK" in r.output

    def test_unknown_rule_id(self, tmp_path: Path) -> None:
        f = tmp_path / "codeguard.toml"
        f.write_text('[codeguard.rules]\ndisable = ["CG-NOPE-1"]\n', encoding="utf-8")
        r = CliRunner().invoke(cli, ["validate", "--config", str(f)])
        assert r.exit_code == 3
        assert "unknown rule" in r.output

    def test_malformed(self, tmp_path: Path) -> None:
        f = tmp_path / "codeguard.toml"
        f.write_text("[codeguard]\nfail_on = 5\n", encoding="utf-8")
        r = CliRunner().invoke(cli, ["validate", "--config", str(f)])
        assert r.exit_code == 3


class TestInit:
    def test_writes_file(self, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        r = runner.invoke(cli, ["init"])
        assert r.exit_code == 0
        assert (tmp_path / "codeguard.toml").exists()
        # and it round-trips through validate
        assert runner.invoke(cli, ["validate"]).exit_code == 0

    def test_refuses_overwrite(self, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.chdir(tmp_path)
        (tmp_path / "codeguard.toml").write_text("[codeguard]\n", encoding="utf-8")
        r = CliRunner().invoke(cli, ["init"])
        assert r.exit_code == 2


class TestRunDemo:
    def test_run_invokes_interactive_demo_menu(self, monkeypatch, tmp_path: Path) -> None:
        script = tmp_path / "demos" / "run_demo.sh"
        script.parent.mkdir()
        script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        calls: list[list[str]] = []

        monkeypatch.setattr(commands, "_find_demo_script", lambda: script)

        def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            assert check is False
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(commands.subprocess, "run", fake_run)

        result = CliRunner().invoke(cli, ["run"])

        assert result.exit_code == 0
        assert calls == [["bash", str(script)]]

    def test_run_reports_missing_demo_suite(self, monkeypatch) -> None:
        monkeypatch.setattr(commands, "_find_demo_script", lambda: None)

        result = CliRunner().invoke(cli, ["run"])

        assert result.exit_code == 1
        assert "demo suite not found" in result.output
