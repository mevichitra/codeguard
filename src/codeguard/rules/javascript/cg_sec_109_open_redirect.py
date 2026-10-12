# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-109 -- redirect to a URL taken from the request (open redirect).

- Server: ``res.redirect(req.query.next)`` / ``res.redirect(302, req.body.url)``
  / ``ctx.redirect(...)`` with request data in the target.
- Browser: ``location.href = ...`` / ``location.assign(...)`` /
  ``location.replace(...)`` / ``window.location = ...`` with data from
  ``location.search`` / ``location.hash`` / ``URLSearchParams``.

Arguments wrapped in ``new URL(...)`` with an origin check, or an allow-list
helper, cannot be seen; suppress with a reason.  CWE-601.
"""

from __future__ import annotations

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import LOCATION_DATA, REQUEST_DATA, arguments, callee_text, calls

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_LOCATION_TARGETS = frozenset(
    {"location", "location.href", "window.location", "window.location.href", "document.location"}
)
_FIX = (
    "Redirect only to relative paths or an allow-list of origins, e.g. "
    "const u = new URL(next, base); if (u.origin === base) res.redirect(u.pathname)."
)


class OpenRedirectJsRule(TreeSitterRule):
    id = "CG-SEC-109"
    title = "Redirect to a URL taken from the request"
    description = (
        "The redirect target comes from the request or the page URL. Attackers use this "
        "to send victims from a trusted domain to a phishing site (open redirect)."
    )
    severity = Severity.MEDIUM
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-601"
    owasp = "A01:2021 - Broken Access Control"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for call in calls(root):
            callee = callee_text(call)
            args = arguments(call)
            if not args:
                continue
            target = args[-1]
            if callee.endswith(".redirect") and REQUEST_DATA.search(target.text()):
                findings.append(self._finding(call, ctx))
            elif callee in (
                "location.assign",
                "location.replace",
                "window.location.assign",
                "window.location.replace",
            ) and LOCATION_DATA.search(target.text()):
                findings.append(self._finding(call, ctx))
        for node in root.walk():
            if node.kind != "assignment_expression":
                continue
            left = node.child_by_field("left")
            right = node.child_by_field("right")
            if (
                left is not None
                and right is not None
                and left.text() in _LOCATION_TARGETS
                and LOCATION_DATA.search(right.text())
            ):
                findings.append(self._finding(node, ctx))
        return findings

    def _finding(self, node: SourceNode, ctx: RuleContext) -> Finding:
        return self._make_finding(node=node, ctx=ctx, fix_suggestion=_FIX, confidence=0.8)


REGISTRY.register(OpenRedirectJsRule())
