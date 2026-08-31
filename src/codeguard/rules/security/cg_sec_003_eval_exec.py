# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-003 — eval() / exec() called with a non-literal argument.

Detects calls to ``eval``, ``exec``, or ``compile`` where the first argument
is not a string literal — meaning the code being executed is dynamic and may
be attacker-controlled.

Why this matters
----------------
``eval()`` and ``exec()`` execute arbitrary Python.  When called with
user-controlled or externally-sourced input they allow remote code execution
(CWE-78, CWE-95, OWASP A03:2021).

AI models frequently generate ``eval(user_input)`` or ``exec(command)``
patterns because they look like concise solutions to dynamic-dispatch problems.

False-positive guidance
-----------------------
``eval("1 + 1")`` with a *literal* string is intentionally excluded — that is
a code smell but not the dangerous case.  If your codebase legitimately calls
``eval`` on trusted, internally-constructed strings, suppress with:
``# codeguard: ignore[CG-SEC-003]``
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule

_DANGEROUS_BUILTINS = frozenset({"eval", "exec", "compile"})

_FIX = (
    "Avoid eval/exec on dynamic input. Use a safe dispatch mechanism "
    "(a dict of callables, importlib, or ast.literal_eval for data parsing)."
)


class EvalExecRule(AstRule):
    """Detect eval/exec/compile called with a non-literal argument."""

    id = "CG-SEC-003"
    title = "eval() / exec() on dynamic input"
    description = (
        "eval(), exec(), or compile() is called with a non-literal argument. "
        "If the argument can be influenced by external input this is a remote "
        "code execution vulnerability."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    cwe = "CWE-95"
    owasp = "A03:2021 - Injection"

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        """Find eval/exec/compile calls with dynamic first arguments."""
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func_name = self._func_name(node)
            if func_name not in _DANGEROUS_BUILTINS:
                continue

            # No arguments at all — unusual but not our concern
            if not node.args:
                continue

            first_arg = node.args[0]
            # Safe case: literal string — eval("1+1") is a code smell, not RCE
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                continue

            findings.append(
                self._make_finding(
                    node=node,
                    filename=filename,
                    description=(
                        f"{func_name}() is called with a non-literal argument. "
                        "If this value is attacker-controlled it enables arbitrary "
                        "code execution."
                    ),
                    fix_suggestion=_FIX,
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _func_name(node: ast.Call) -> str:
        """Return the bare function name for simple Name calls, else ''."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        return ""


REGISTRY.register(EvalExecRule())
