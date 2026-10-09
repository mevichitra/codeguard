# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-108 -- TLS certificate verification disabled (Node.js).

- ``{ rejectUnauthorized: false }`` (https.Agent, tls.connect, axios, got, ...)
- ``{ strictSSL: false }`` (request)
- ``process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'``

CWE-295.
"""

from __future__ import annotations

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import is_false, property_key, string_value

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_KEYS = frozenset({"rejectUnauthorized", "strictSSL"})
_ENV = "NODE_TLS_REJECT_UNAUTHORIZED"
_FIX = (
    "Keep verification on. To trust a private CA, pass it explicitly: "
    "new https.Agent({ ca: fs.readFileSync('ca.pem') }) or NODE_EXTRA_CA_CERTS."
)


class TlsVerifyDisabledJsRule(TreeSitterRule):
    id = "CG-SEC-108"
    title = "TLS certificate verification disabled"
    description = (
        "Certificate verification is turned off, so the connection accepts any "
        "certificate. Anyone on the network path can read and modify the traffic."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-295"
    owasp = "A07:2021 - Identification and Authentication Failures"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for node in root.walk():
            if node.kind == "pair" and property_key(node) in _KEYS:
                value = node.child_by_field("value")
                if value is not None and is_false(value):
                    findings.append(self._make_finding(node=node, ctx=ctx, fix_suggestion=_FIX))
            elif node.kind == "assignment_expression":
                left = node.child_by_field("left")
                right = node.child_by_field("right")
                if left is None or right is None or not left.text().endswith(_ENV):
                    continue
                if string_value(right) == "0" or right.text() == "0":
                    findings.append(self._make_finding(node=node, ctx=ctx, fix_suggestion=_FIX))
        return findings


REGISTRY.register(TlsVerifyDisabledJsRule())
