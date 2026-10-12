# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-107 -- ``crypto.createHash('md5' | 'sha1')`` for a security value.

Reported when the result is bound to a name (or computed in a function) that
reads like a password, token, or signature.  CWE-328.
"""

from __future__ import annotations

import re

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import arguments, callee_text, calls, string_value

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_WEAK = frozenset({"md5", "sha1"})
_CONTEXT = re.compile(
    r"(?i)(password|passwd|pwd|secret|token|signature|hmac|salt|credential|otp|api_?key|auth)"
)
_FIX = (
    "Hash passwords with a slow KDF (crypto.scrypt, argon2, bcrypt). For tokens and "
    "signatures use crypto.createHmac('sha256', key) or createHash('sha256')."
)


class WeakHashJsRule(TreeSitterRule):
    id = "CG-SEC-107"
    title = "Weak hash (MD5 / SHA-1) used for a security value"
    description = (
        "MD5 and SHA-1 are broken for security: collisions are practical and both are "
        "fast enough to brute-force passwords. The surrounding names suggest this hash "
        "protects a password, token, or signature."
    )
    severity = Severity.MEDIUM
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-328"
    owasp = "A02:2021 - Cryptographic Failures"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for call in calls(root):
            if not callee_text(call).endswith("createHash"):
                continue
            args = arguments(call)
            algo = string_value(args[0]) if args else None
            if algo is None or algo.lower().replace("-", "") not in _WEAK:
                continue
            if not _security_context(call):
                continue
            findings.append(
                self._make_finding(node=call, ctx=ctx, fix_suggestion=_FIX, confidence=0.7)
            )
        return findings


_NAMED = {
    "variable_declarator": "name",
    "assignment_expression": "left",
    "pair": "key",
    "function_declaration": "name",
    "method_definition": "name",
    "public_field_definition": "name",
}


def _security_context(node: SourceNode) -> bool:
    for anc in node.ancestors():
        field = _NAMED.get(anc.kind)
        if field is not None:
            named = anc.child_by_field(field)
            if named is not None and _CONTEXT.search(named.text()):
                return True
        if anc.kind == "program":
            break
    return False


REGISTRY.register(WeakHashJsRule())
