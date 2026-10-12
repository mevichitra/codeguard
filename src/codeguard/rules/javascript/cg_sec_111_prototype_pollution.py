# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-111 -- deep merge of request data (prototype pollution).

``_.merge`` / ``_.mergeWith`` / ``_.defaultsDeep`` / ``deepmerge`` /
``merge`` / ``$.extend(true, ...)`` with request data as a source object.  A
body like ``{"__proto__": {"isAdmin": true}}`` then reaches
``Object.prototype`` in vulnerable merge implementations.  ``Object.assign``
is shallow and not reported.  CWE-1321.
"""

from __future__ import annotations

import re

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import REQUEST_DATA, arguments, callee_text, calls

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_MERGE = re.compile(
    r"(?:^|\.)(?:merge|mergeWith|defaultsDeep|deepmerge|deepMerge|mergeDeep)$|"
    r"^(?:\$|jQuery)\.extend$"
)
_FIX = (
    "Copy only the fields you expect (const { name, email } = req.body), validate the "
    "body with a schema, or merge into Object.create(null). Keep lodash >= 4.17.21."
)


class PrototypePollutionRule(TreeSitterRule):
    id = "CG-SEC-111"
    title = "Deep merge of request data (prototype pollution)"
    description = (
        "Request data is deep-merged into an object. A key such as '__proto__' can "
        "modify Object.prototype and change behaviour across the whole application."
    )
    severity = Severity.MEDIUM
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-1321"
    owasp = "A08:2021 - Software and Data Integrity Failures"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for call in calls(root):
            callee = callee_text(call)
            if not _MERGE.search(callee):
                continue
            args = arguments(call)
            if callee.endswith("extend") and (not args or args[0].text() != "true"):
                continue
            if any(REQUEST_DATA.search(a.text()) for a in args[1:]):
                findings.append(
                    self._make_finding(node=call, ctx=ctx, fix_suggestion=_FIX, confidence=0.6)
                )
        return findings


REGISTRY.register(PrototypePollutionRule())
