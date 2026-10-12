# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-005 — a non-literal command run through a shell.

Two cases, both CWE-78 / OWASP A03:2021:

- ``subprocess.run`` / ``call`` / ``Popen`` / ``check_output`` / ``check_call``
  with ``shell=True`` and a non-literal command.
- ``os.system`` / ``os.popen`` / ``subprocess.getoutput`` /
  ``subprocess.getstatusoutput`` with a non-literal command — these always use
  a shell, there is no ``shell=`` keyword to check.

Import aliases are resolved, so ``from os import system`` and
``import subprocess as sp`` are covered.

Why this matters
----------------
When a command string is interpreted by the OS shell and any part of it is
attacker-controlled, the attacker can inject arbitrary shell commands.

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
from codeguard.engine.rule import AstRule
from codeguard.rules._pyimports import ImportMap
from codeguard.rules._pysinks import command_is_literal, shell_target

_FIX = (
    "Pass the command as a list with shell=False: "
    "subprocess.run(['git', 'status'], shell=False). "
    "If a shell is required, validate and sanitize every interpolated value with shlex.quote()."
)


class ShellInjectionRule(AstRule):
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

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        """Find shell command injection via subprocess / os.system."""
        findings: list[Finding] = []
        imports = ImportMap.from_tree(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            target = shell_target(node, imports)
            if target is None or command_is_literal(node):
                continue

            module, method = target
            findings.append(
                self._make_finding(
                    node=node,
                    filename=filename,
                    description=(
                        f"{module}.{method}() runs a non-literal command through a shell. "
                        "If any part of the command is attacker-controlled, this enables "
                        "shell command injection."
                    ),
                    fix_suggestion=_FIX,
                )
            )

        return findings


REGISTRY.register(ShellInjectionRule())
