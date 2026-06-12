# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-005 — subprocess called with shell=True and a non-literal command.

Detects calls to subprocess.run / Popen / call / check_output / check_call
(and os.system) with ``shell=True`` where the command argument is not a
string literal.

Why this matters
----------------
When ``shell=True`` is passed to subprocess, the command string is interpreted
by the OS shell.  If any part of that string is attacker-controlled, the
attacker can inject arbitrary shell commands (CWE-78, OWASP A03:2021).

AI models routinely generate ``subprocess.run(f"git {user_arg}", shell=True)``
because it looks clean and concise.  It is not.

Safe patterns NOT flagged
-------------------------
- ``subprocess.run("ls -la", shell=True)``  — literal string, no injection vector
- ``subprocess.run(["git", "status"])``       — list form without shell=True
- ``subprocess.run(cmd, shell=False)``        — shell disabled

False-positive guidance
-----------------------
If the command is constructed from entirely trusted, validated values you can
suppress: ``# codeguard: ignore[CG-SEC-005]``

Better: switch to the list form (``shell=False``).
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import Rule

_SUBPROCESS_FUNCS = frozenset(
    {"run", "call", "Popen", "check_output", "check_call", "getoutput", "getstatusoutput"}
)
_SUBPROCESS_MODULES = frozenset({"subprocess"})

_FIX = (
    "Pass the command as a list with shell=False: "
    "subprocess.run(['git', 'status'], shell=False). "
    "If shell=True is required, validate and sanitize every interpolated value with shlex.quote()."
)


class ShellInjectionRule(Rule):
    """Detect subprocess calls with shell=True and a non-literal command."""

    id = "CG-SEC-005"
    title = "subprocess with shell=True and dynamic command"
    description = (
        "subprocess is called with shell=True and the command argument is not a "
        "string literal. If any part of the command is attacker-controlled, this "
        "enables shell command injection."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    cwe = "CWE-78"
    owasp = "A03:2021 - Injection"

    def check(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        """Find subprocess calls with shell=True and dynamic commands."""
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not self._is_subprocess_call(node):
                continue
            if not self._has_shell_true(node):
                continue
            if self._command_is_literal(node):
                continue

            findings.append(
                self._make_finding(
                    node=node,
                    filename=filename,
                    fix_suggestion=_FIX,
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_subprocess_call(node: ast.Call) -> bool:
        """Return True for subprocess.{run,Popen,...} or os.system."""
        func = node.func
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                module = func.value.id
                method = func.attr
                if module in _SUBPROCESS_MODULES and method in _SUBPROCESS_FUNCS:
                    return True
                if module == "os" and method == "system":
                    return True
        # Direct name: Popen(...) after from subprocess import Popen
        if isinstance(func, ast.Name) and func.id in _SUBPROCESS_FUNCS:
            return True
        return False

    @staticmethod
    def _has_shell_true(node: ast.Call) -> bool:
        """Return True if shell=True is explicitly passed."""
        for kw in node.keywords:
            if kw.arg == "shell":
                val = kw.value
                # shell=True  or  shell=1
                if isinstance(val, ast.Constant) and val.value:
                    return True
        return False

    @staticmethod
    def _command_is_literal(node: ast.Call) -> bool:
        """Return True if the command arg is a plain string literal (safe case)."""
        if not node.args:
            # All keyword args — look for args=
            for kw in node.keywords:
                if kw.arg == "args":
                    return isinstance(kw.value, ast.Constant)
            return True  # no command at all — not our concern

        first = node.args[0]
        # List of literals is fine too: ["ls", "-la"]
        if isinstance(first, ast.List):
            return all(isinstance(elt, ast.Constant) for elt in first.elts)
        return isinstance(first, ast.Constant)


REGISTRY.register(ShellInjectionRule())
