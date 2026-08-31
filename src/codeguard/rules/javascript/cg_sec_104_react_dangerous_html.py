# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-104 -- React dangerouslySetInnerHTML with a non-literal value.

``<div dangerouslySetInnerHTML={{ __html: value }} />`` bypasses React's XSS
escaping.  If ``value`` is not a literal, the HTML must be sanitized first.
CWE-79.
"""

from __future__ import annotations

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import is_literal

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_FIX = (
    "Sanitize the HTML with DOMPurify before passing it to __html, or render the "
    "value as text instead of raw HTML."
)


class ReactDangerousHtmlRule(TreeSitterRule):
    id = "CG-SEC-104"
    title = "dangerouslySetInnerHTML with a non-literal value"
    description = (
        "dangerouslySetInnerHTML injects raw HTML, bypassing React's escaping. "
        "The __html value here is not a literal; if it is attacker-controlled "
        "this is a cross-site scripting vulnerability."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-79"
    owasp = "A03:2021 - Injection"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for node in root.walk():
            if node.kind != "pair":
                continue
            key = node.child_by_field("key")
            value = node.child_by_field("value")
            if key is None or value is None or key.text().strip("'\"") != "__html":
                continue
            if not is_literal(value):
                findings.append(self._make_finding(node=node, ctx=ctx, fix_suggestion=_FIX))
        return findings


REGISTRY.register(ReactDangerousHtmlRule())
