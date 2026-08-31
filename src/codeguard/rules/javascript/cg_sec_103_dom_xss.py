# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-103 -- DOM-based XSS sink assigned a non-literal.

Flags ``el.innerHTML = x`` / ``el.outerHTML = x`` / ``el.insertAdjacentHTML(pos, x)``
/ ``document.write(x)`` where the HTML is not a string literal.  CWE-79.
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
_SINK_PROPS = frozenset({"innerHTML", "outerHTML"})
_SINK_CALLS = frozenset({"write", "writeln", "insertAdjacentHTML"})
_FIX = (
    "Set textContent, or sanitize the HTML with a library like DOMPurify before "
    "assigning it. Prefer DOM APIs (createElement / append) over HTML strings."
)


class DomXssRule(TreeSitterRule):
    id = "CG-SEC-103"
    title = "DOM XSS sink assigned a non-literal value"
    description = (
        "A non-literal value is written to innerHTML / outerHTML / document.write "
        "/ insertAdjacentHTML. If it contains attacker-controlled data the browser "
        "will execute injected script."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-79"
    owasp = "A03:2021 - Injection"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []

        for node in root.walk():
            if node.kind == "assignment_expression":
                left = node.child_by_field("left")
                right = node.child_by_field("right")
                if left is None or right is None or left.kind != "member_expression":
                    continue
                prop = left.child_by_field("property")
                if prop and prop.text() in _SINK_PROPS and not is_literal(right):
                    findings.append(self._make_finding(node=node, ctx=ctx, fix_suggestion=_FIX))

        for call in calls(root):
            callee = callee_text(call)
            base = callee.rsplit(".", 1)[-1]
            if base not in _SINK_CALLS or "." not in callee:
                continue
            args = arguments(call)
            html_arg = args[-1] if base == "insertAdjacentHTML" else (args[0] if args else None)
            if html_arg is not None and not is_literal(html_arg):
                findings.append(self._make_finding(node=call, ctx=ctx, fix_suggestion=_FIX))

        return findings


REGISTRY.register(DomXssRule())
