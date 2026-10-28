# SPDX-License-Identifier: Apache-2.0
"""Integration tests for `codeguard ci` and the new formats / --baseline flag."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from codeguard.cli.main import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, cli

VULN = 'import os\npassword = "seekrit123"\nos.system("rm " + a)\n'


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    for rel, body in files.items():
        (tmp_path / rel).write_text(body, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


class TestBaselineFlag:
    def test_baselined_finding_does_not_fail(self, tmp_path: Path) -> None:
        _repo(tmp_path, {"a.py": VULN})
        r = CliRunner()
        assert (
            r.invoke(
                cli, ["baseline", "create", str(tmp_path), "-o", str(tmp_path / "bl.json")]
            ).exit_code
            == 0
        )
        res = r.invoke(cli, ["scan", str(tmp_path), "--baseline", str(tmp_path / "bl.json")])
        assert res.exit_code == EXIT_OK

    def test_new_finding_after_baseline_fails(self, tmp_path: Path) -> None:
        _repo(tmp_path, {"a.py": 'password = "seekrit123"\n'})
        r = CliRunner()
        r.invoke(cli, ["baseline", "create", str(tmp_path), "-o", str(tmp_path / "bl.json")])
        (tmp_path / "a.py").write_text(VULN, encoding="utf-8")
        res = r.invoke(
            cli,
            ["scan", str(tmp_path), "--baseline", str(tmp_path / "bl.json"), "--format", "json"],
        )
        assert res.exit_code == EXIT_FINDINGS
        ids = {x["rule_id"] for x in json.loads(res.output)["results"]}
        assert ids == {"CG-SEC-005"}  # the hardcoded secret is baselined, hidden

    def test_baseline_update_and_prune(self, tmp_path: Path) -> None:
        _repo(tmp_path, {"a.py": 'password = "seekrit123"\n'})
        r = CliRunner()
        bl = str(tmp_path / "bl.json")
        r.invoke(cli, ["baseline", "create", str(tmp_path), "-o", bl])
        (tmp_path / "a.py").write_text(VULN, encoding="utf-8")
        upd = r.invoke(cli, ["baseline", "update", str(tmp_path), "-b", bl])
        assert "+1" in upd.output
        (tmp_path / "a.py").write_text("clean = 1\n", encoding="utf-8")
        prune = r.invoke(cli, ["baseline", "prune", str(tmp_path), "-b", bl])
        assert "-2" in prune.output

    def test_renamed_file_stays_baselined(self, tmp_path: Path) -> None:
        _repo(tmp_path, {"a.py": VULN})
        r = CliRunner()
        bl = str(tmp_path / "bl.json")
        r.invoke(cli, ["baseline", "create", str(tmp_path), "-o", bl])
        assert json.loads(Path(bl).read_text())["commit"]
        (tmp_path / "a.py").rename(tmp_path / "b.py")
        _git(tmp_path, "add", "-A")
        res = r.invoke(
            cli,
            ["scan", str(tmp_path), "--baseline", bl, "--format", "json", "--show-suppressed"],
        )
        assert res.exit_code == EXIT_OK
        results = json.loads(res.output)["results"]
        assert results and all(x["baselined"] for x in results)
        assert {x["match"]["pass"] for x in results} == {"stmt"}

    def test_strict_mode_reports_a_pasted_copy(self, tmp_path: Path) -> None:
        _repo(tmp_path, {"a.py": 'import os\nos.system("rm " + a)\nprint(x)\n'})
        r = CliRunner()
        bl = str(tmp_path / "bl.json")
        r.invoke(cli, ["baseline", "create", str(tmp_path), "-o", bl])
        # Both neighbours change, so neither copy is the better candidate.
        (tmp_path / "a.py").write_text(
            'import sys\nos.system("rm " + a)\nos.system("rm " + a)\nprint(y)\n',
            encoding="utf-8",
        )
        args = ["scan", str(tmp_path), "--baseline", bl, "--format", "json", "--show-suppressed"]
        res = r.invoke(cli, args)
        assert res.exit_code == EXIT_FINDINGS
        results = json.loads(res.output)["results"]
        assert [(x["baselined"], x["match"]["status"]) for x in results] == [
            (True, "ambiguous"),
            (False, "new"),
        ]
        strict = r.invoke(cli, [*args, "--baseline-strict"])
        results = json.loads(strict.output)["results"]
        assert [(x["baselined"], x["match"]["status"]) for x in results] == [
            (False, "ambiguous"),
            (False, "new"),
        ]


class TestCi:
    def test_scans_only_changed_files(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"old.py": "x = 1\n"})
        _git(repo, "checkout", "-b", "feature")
        (repo / "new.py").write_text(VULN, encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "add new")

        r = CliRunner().invoke(cli, ["ci", str(repo), "--diff", "main", "--format", "json"])
        assert r.exit_code == EXIT_FINDINGS
        files = {x["location"]["file"] for x in json.loads(r.output)["results"]}
        assert all("new.py" in f for f in files)

    def test_default_format_is_github(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"a.py": "x = 1\n"})
        _git(repo, "checkout", "-b", "feature")
        (repo / "a.py").write_text(VULN, encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "work")
        r = CliRunner().invoke(cli, ["ci", str(repo), "--diff", "main"])
        assert "::error " in r.output

    def test_ci_outside_git_repo_exits_two(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        r = CliRunner().invoke(cli, ["ci", str(tmp_path)])
        assert r.exit_code == EXIT_USAGE


class TestFormats:
    def test_github(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(VULN, encoding="utf-8")
        r = CliRunner().invoke(cli, ["scan", str(tmp_path / "a.py"), "--format", "github"])
        assert r.output.startswith("::error ")
        assert "file=" in r.output and "CG-SEC-005" in r.output

    def test_rdjson(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(VULN, encoding="utf-8")
        r = CliRunner().invoke(cli, ["scan", str(tmp_path / "a.py"), "--format", "rdjson"])
        data = json.loads(r.output)
        assert data["source"]["name"] == "codeguard"
        assert data["diagnostics"][0]["severity"] == "ERROR"

    def test_junit(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(VULN, encoding="utf-8")
        r = CliRunner().invoke(cli, ["scan", str(tmp_path / "a.py"), "--format", "junit"])
        assert r.output.startswith("<?xml")
        assert '<testsuites name="codeguard"' in r.output
        assert "<failure " in r.output
