# SPDX-License-Identifier: Apache-2.0
"""Integration tests for `codeguard scan`."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from codeguard.cli.main import EXIT_CONFIG, EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, cli

VULN = 'import os\npassword = "s"\nos.system("x " + a)\n'


def _proj(tmp_path: Path, files: dict[str, str]) -> Path:
    (tmp_path / ".git").mkdir()
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return tmp_path


def test_clean_tree_exits_zero(tmp_path: Path) -> None:
    _proj(tmp_path, {"ok.py": "x = 1\n"})
    r = CliRunner().invoke(cli, ["scan", str(tmp_path)])
    assert r.exit_code == EXIT_OK


def test_findings_exit_one(tmp_path: Path) -> None:
    _proj(tmp_path, {"bad.py": VULN})
    r = CliRunner().invoke(cli, ["scan", str(tmp_path)])
    assert r.exit_code == EXIT_FINDINGS
    assert "CG-SEC-002" in r.output


def test_fail_on_high_ignores_lower(tmp_path: Path) -> None:
    _proj(tmp_path, {"bad.py": VULN, "cfg": ""})
    (tmp_path / "codeguard.toml").write_text(
        '[codeguard.severity_remap]\nCG-SEC-002 = "low"\nCG-SEC-005 = "low"\n',
        encoding="utf-8",
    )
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--fail-on", "high"])
    assert r.exit_code == EXIT_OK  # findings exist but none are >= high


def test_exit_zero_flag(tmp_path: Path) -> None:
    _proj(tmp_path, {"bad.py": VULN})
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--exit-zero"])
    assert r.exit_code == EXIT_OK


def test_exclude_glob(tmp_path: Path) -> None:
    _proj(tmp_path, {"src/bad.py": VULN, "vendor/bad.py": VULN})
    r = CliRunner().invoke(
        cli, ["scan", str(tmp_path), "--exclude", "vendor/**", "--format", "json"]
    )
    files = {res["location"]["file"] for res in json.loads(r.output)["results"]}
    assert all("vendor" not in f for f in files)
    assert any("src" in f for f in files)


def test_gitignore_respected(tmp_path: Path) -> None:
    _proj(tmp_path, {"keep.py": VULN, "skip.py": VULN, ".gitignore": "skip.py\n"})
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--format", "json"])
    files = {res["location"]["file"] for res in json.loads(r.output)["results"]}
    assert not any("skip.py" in f for f in files)


def test_disable_rule_via_config(tmp_path: Path) -> None:
    _proj(tmp_path, {"bad.py": VULN})
    (tmp_path / "codeguard.toml").write_text(
        '[codeguard.rules]\ndisable = ["CG-SEC-002"]\n', encoding="utf-8"
    )
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--format", "json"])
    ids = {res["rule_id"] for res in json.loads(r.output)["results"]}
    assert "CG-SEC-002" not in ids
    assert "CG-SEC-005" in ids


def test_path_override_suppresses(tmp_path: Path) -> None:
    _proj(tmp_path, {"migrations/m.py": VULN})
    (tmp_path / "codeguard.toml").write_text(
        '[[codeguard.overrides]]\npath = "migrations/**"\ndisable = ["ALL"]\n',
        encoding="utf-8",
    )
    r = CliRunner().invoke(cli, ["scan", str(tmp_path)])
    assert r.exit_code == EXIT_OK


def test_stdin(tmp_path: Path) -> None:
    r = CliRunner().invoke(cli, ["scan", "-", "--format", "json"], input=VULN)
    assert r.exit_code == EXIT_FINDINGS
    assert json.loads(r.output)["summary"]["findings"] >= 1


def test_bad_config_exits_three(tmp_path: Path) -> None:
    _proj(tmp_path, {"a.py": "x=1\n"})
    (tmp_path / "codeguard.toml").write_text("[codeguard]\nfail_on = 'nope'\n", encoding="utf-8")
    r = CliRunner().invoke(
        cli, ["scan", str(tmp_path), "--config", str(tmp_path / "codeguard.toml")]
    )
    assert r.exit_code == EXIT_CONFIG


def test_missing_path_exits_two(tmp_path: Path) -> None:
    r = CliRunner().invoke(cli, ["scan", str(tmp_path / "nope")])
    assert r.exit_code == EXIT_USAGE


def test_unknown_rule_exits_two(tmp_path: Path) -> None:
    _proj(tmp_path, {"a.py": "x=1\n"})
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--rule", "CG-NOPE-001"])
    assert r.exit_code == EXIT_USAGE


def test_severity_alias_warns(tmp_path: Path) -> None:
    _proj(tmp_path, {"a.py": "x=1\n"})
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--severity", "high"])
    assert "deprecated" in r.output
