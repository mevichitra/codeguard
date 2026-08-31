# SPDX-License-Identifier: Apache-2.0
"""Tests for CG-SEC-005: subprocess with shell=True and dynamic command."""

from __future__ import annotations

from codeguard.engine.runner import AnalysisRunner
from tests.conftest import load_fixture

RULE_ID = "CG-SEC-005"
RUNNER = AnalysisRunner(rule_ids=[RULE_ID])


def active_findings(source: str) -> list:
    return [f for f in RUNNER.run(source, filename="test.py") if not f.suppressed]


class TestCGSEC005Vulnerable:
    def test_run_fstring_shell_true(self) -> None:
        src = 'import subprocess\nsubprocess.run(f"echo {cmd}", shell=True)\n'
        assert len(active_findings(src)) >= 1

    def test_call_concat_shell_true(self) -> None:
        src = 'import subprocess\nsubprocess.call("git checkout " + branch, shell=True)\n'
        assert len(active_findings(src)) >= 1

    def test_popen_fstring_shell_true(self) -> None:
        src = 'import subprocess\nsubprocess.Popen(f"ls {path}", shell=True)\n'
        assert len(active_findings(src)) >= 1

    def test_check_output_variable_shell_true(self) -> None:
        src = "import subprocess\nsubprocess.check_output(cmd, shell=True)\n"
        assert len(active_findings(src)) >= 1

    def test_os_system_concat(self) -> None:
        # os.system always uses a shell -- no shell= keyword to check (issue #3)
        src = 'import os\nos.system("git checkout " + branch)\n'
        assert len(active_findings(src)) >= 1

    def test_os_popen_fstring(self) -> None:
        src = 'import os\nos.popen(f"cat {path}")\n'
        assert len(active_findings(src)) >= 1

    def test_subprocess_getoutput_variable(self) -> None:
        src = "import subprocess\nsubprocess.getoutput(cmd)\n"
        assert len(active_findings(src)) >= 1

    def test_from_import_alias(self) -> None:
        src = 'from os import system as sh\nsh("rm -rf " + target)\n'
        assert len(active_findings(src)) >= 1

    def test_module_alias(self) -> None:
        src = 'import subprocess as sp\nsp.run(f"echo {x}", shell=True)\n'
        assert len(active_findings(src)) >= 1

    def test_vulnerable_fixture(self) -> None:
        src = load_fixture("python", "security", "cg_sec_005", "vulnerable")
        findings = active_findings(src)
        assert len(findings) >= 1, "Vulnerable fixture produced no findings"
        assert all(f.rule_id == RULE_ID for f in findings)


class TestCGSEC005Safe:
    def test_literal_with_shell_true(self) -> None:
        # Literal string — no injection vector
        src = 'import subprocess\nsubprocess.run("ls -la", shell=True)\n'
        assert active_findings(src) == []

    def test_list_form_no_shell(self) -> None:
        src = 'import subprocess\nsubprocess.run(["git", "checkout", branch])\n'
        assert active_findings(src) == []

    def test_list_form_shell_false(self) -> None:
        src = 'import subprocess\nsubprocess.run(["ls", path], shell=False)\n'
        assert active_findings(src) == []

    def test_variable_shell_false(self) -> None:
        # shell=False with a variable is not a shell injection
        src = "import subprocess\nsubprocess.run(cmd, shell=False)\n"
        assert active_findings(src) == []

    def test_os_system_literal(self) -> None:
        # Literal command -- no injection vector (issue #3)
        src = 'import os\nos.system("ls -la")\n'
        assert active_findings(src) == []

    def test_unrelated_bare_run(self) -> None:
        # A local function named run(), not imported from subprocess
        src = 'def run(x): ...\nrun(cmd + " here")\n'
        assert active_findings(src) == []

    def test_safe_fixture(self) -> None:
        src = load_fixture("python", "security", "cg_sec_005", "safe")
        findings = active_findings(src)
        assert findings == [], f"Safe fixture produced unexpected findings: {findings}"
