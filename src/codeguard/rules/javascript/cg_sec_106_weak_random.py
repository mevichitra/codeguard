# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-106 -- Math.random() used for something security-sensitive.

``Math.random()`` is not cryptographically secure.  Using it to build a token,
session id, password, nonce, salt, OTP, or API key is CWE-338.  The rule only
fires when the surrounding binding name signals a security use, to keep the
false-positive rate low (confidence 0.8).
"""

from __future__ import annotations

import re

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import callee_text, calls

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_SECURITY_WORD = re.compile(
    r"(?i)(token|secret|password|passwd|nonce|salt|otp|apikey|api_key|"
    r"session|session_id|sessionid|csrf|uuid|guid|random_?id|verification|"
    r"reset_?code|auth)"
)
_NAME_BEARING = {
    "variable_declarator": "name",
    "assignment_expression": "left",
    "pair": "key",
    "public_field_definition": "name",
}
_FIX = (
    "Use a cryptographically secure source: crypto.randomBytes(),"
    " crypto.randomUUID(), or the Web Crypto API (crypto.getRandomValues())."
)


class WeakRandomRule(TreeSitterRule):
    id = "CG-SEC-106"
    title = "Math.random() used for a security value"
    description = (
        "Math.random() is not cryptographically secure. It is being used to "
        "produce a value whose name indicates a token, secret, id, nonce, or "
        "similar -- an attacker can predict the output."
    )
    severity = Severity.MEDIUM
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-338"
    owasp = "A02:2021 - Cryptographic Failures"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for call in calls(root):
            if callee_text(call) != "Math.random":
                continue
            name = _enclosing_binding_name(call)
            if name and _SECURITY_WORD.search(name):
                findings.append(
                    self._make_finding(node=call, ctx=ctx, fix_suggestion=_FIX, confidence=0.8)
                )
        return findings


def _enclosing_binding_name(node: SourceNode, *, depth: int = 6) -> str | None:
    """Walk up to *depth* ancestors looking for a binding, return its name text."""
    native = node.native
    for _ in range(depth):
        parent = getattr(native, "parent", None)
        if parent is None:
            return None
        field = _NAME_BEARING.get(parent.type)
        if field is not None:
            target = parent.child_by_field_name(field)
            if target is not None and target.text is not None:
                return str(target.text.decode("utf-8", "replace"))
        native = parent
    return None


REGISTRY.register(WeakRandomRule())
