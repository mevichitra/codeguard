# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-101 -- dynamic code execution in JavaScript / TypeScript.

Flags:
  - ``eval(x)`` where *x* is not a literal
  - ``new Function(..., body)`` where an argument is not a literal
  - ``setTimeout("...", n)`` / ``setInterval("...", n)`` -- passing a string to a
    timer is an implicit ``eval``

CWE-95 (CWE-94), OWASP A03:2021.  These are the classic "run a string as code"
sinks; AI-generated code reaches for them for dynamic dispatch.
"""

from __future__ import annotations

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import arguments, callee_text, calls, is_literal, new_expressions

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_TIMERS = frozenset({"setTimeout", "setInterval"})
_FIX = (
    "Do not execute strings as code. Use a lookup table of functions, dynamic "
    "import(), or pass a function (not a string) to setTimeout/setInterval."
)


class DynamicCodeExecutionRule(TreeSitterRule):
    id = "CG-SEC-101"
    title = "Dynamic code execution (eval / Function / string timer)"
    description = (
        "A string is executed as code via eval(), new Function(), or a string "
        "argument to setTimeout/setInterval. If any part of it is attacker-"
        "controlled this is remote code execution."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-95"
    owasp = "A03:2021 - Injection"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []

        for call in calls(root):
            base = callee_text(call).rsplit(".", 1)[-1]
            args = arguments(call)
            if not args:
                continue
            if base == "eval" and not is_literal(args[0]):
                findings.append(self._make_finding(node=call, ctx=ctx, fix_suggestion=_FIX))
            elif base in _TIMERS and args[0].kind in ("string", "template_string"):
                findings.append(
                    self._make_finding(
                        node=call,
                        ctx=ctx,
                        description=(
                            f"{base}() is called with a string. The string is run through "
                            "eval() when the timer fires. Pass a function instead."
                        ),
                        fix_suggestion=_FIX,
                    )
                )

        for new_expr in new_expressions(root):
            if callee_text(new_expr).rsplit(".", 1)[-1] != "Function":
                continue
            args = arguments(new_expr)
            if args and not all(is_literal(a) for a in args):
                findings.append(
                    self._make_finding(
                        node=new_expr,
                        ctx=ctx,
                        description=(
                            "new Function() builds a function from a string body. If the "
                            "body is attacker-controlled this is arbitrary code execution."
                        ),
                        fix_suggestion=_FIX,
                    )
                )

        return findings


REGISTRY.register(DynamicCodeExecutionRule())
