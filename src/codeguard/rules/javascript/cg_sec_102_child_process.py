# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-102 -- shell command injection via child_process.

``child_process.exec`` / ``execSync`` run their argument through ``/bin/sh``.
With a non-literal command that is CWE-78.  ``execFile`` / ``spawn`` /
``spawnSync`` do not use a shell (unless ``shell: true``) and are the fix.
"""

from __future__ import annotations

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import arguments, callee_text, calls, is_literal

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_SHELL_FUNCS = frozenset({"exec", "execSync"})
_FIX = (
    "Use execFile() / spawn() with an argument array and no shell: "
    "execFile('git', ['checkout', branch]). If a shell is unavoidable, validate "
    "every interpolated value."
)


class ChildProcessShellRule(TreeSitterRule):
    id = "CG-SEC-102"
    title = "child_process.exec with a dynamic command"
    description = (
        "child_process.exec / execSync run the command through a shell. If the "
        "command string is not a literal and any part is attacker-controlled, "
        "this is shell command injection."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-78"
    owasp = "A03:2021 - Injection"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for call in calls(root):
            callee = callee_text(call)
            base = callee.rsplit(".", 1)[-1]
            if base not in _SHELL_FUNCS:
                continue
            # A bare exec() that isn't a member access is probably unrelated.
            if base == callee and "." not in callee:
                continue
            args = arguments(call)
            if args and not is_literal(args[0]):
                findings.append(self._make_finding(node=call, ctx=ctx, fix_suggestion=_FIX))
        return findings


REGISTRY.register(ChildProcessShellRule())
