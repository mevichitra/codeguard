# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-105 -- hardcoded secret in JavaScript / TypeScript.

A non-trivial string literal assigned to an identifier whose name reads like a
credential (``password``, ``apiKey``, ``token``, ...).  CWE-798.  Mirrors the
Python rule CG-SEC-002; confidence 0.9 because placeholder values in examples
trip it.
"""

from __future__ import annotations

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import looks_like_secret

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_MIN_LEN = 3
_FIX = "Load secrets from process.env or a secrets manager; never commit them."

# (node kind, name field, value field)
_BINDINGS = (
    ("variable_declarator", "name", "value"),
    ("assignment_expression", "left", "right"),
    ("pair", "key", "value"),
    ("public_field_definition", "name", "value"),
)


class HardcodedSecretRule(TreeSitterRule):
    id = "CG-SEC-105"
    title = "Hardcoded secret"
    description = (
        "A string literal is assigned to an identifier whose name indicates a "
        "credential (password, API key, token, ...). Hardcoded secrets get "
        "committed and are trivially discoverable."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-798"
    owasp = "A07:2021 - Identification and Authentication Failures"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for node in root.walk():
            for kind, name_field, value_field in _BINDINGS:
                if node.kind != kind:
                    continue
                name = node.child_by_field(name_field)
                value = node.child_by_field(value_field)
                if name is None or value is None:
                    continue
                if value.kind != "string" or len(value.text()) - 2 < _MIN_LEN:
                    continue
                ident = name.text().strip("'\"")
                if looks_like_secret(ident):
                    findings.append(
                        self._make_finding(
                            node=node,
                            ctx=ctx,
                            description=f"{self.description} (identifier: {ident!r})",
                            fix_suggestion=_FIX,
                            confidence=0.9,
                        )
                    )
        return findings


REGISTRY.register(HardcodedSecretRule())
