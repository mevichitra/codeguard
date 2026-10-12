# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-006 -- MD5 / SHA-1 used for a security value.

``hashlib.md5`` / ``hashlib.sha1`` / ``hashlib.new("md5" | "sha1")`` where the
result is bound to, or computed in a function named like, a password, token,
signature, or secret.  Checksums and cache keys are not reported, and
``usedforsecurity=False`` opts a call out explicitly.  CWE-328.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules._pyimports import ImportMap
from codeguard.rules._pyparents import PyParents

_WEAK = frozenset({"md5", "sha1"})
_FIX = (
    "Hash passwords with a slow, salted KDF (hashlib.scrypt, argon2, bcrypt). For "
    "tokens and signatures use hashlib.sha256 or hmac with SHA-256. If this is not "
    "security-related, pass usedforsecurity=False."
)


class WeakHashRule(AstRule):
    id = "CG-SEC-006"
    title = "Weak hash (MD5 / SHA-1) used for a security value"
    description = (
        "MD5 and SHA-1 are broken for security purposes: collisions are practical and "
        "both are fast enough to brute-force passwords. The surrounding names suggest "
        "this hash protects a password, token, or signature."
    )
    severity = Severity.MEDIUM
    category = Category.SECURITY
    cwe = "CWE-328"
    owasp = "A02:2021 - Cryptographic Failures"

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        imports = ImportMap.from_tree(tree)
        parents: PyParents | None = None
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            algo = _weak_algorithm(node, imports)
            if algo is None or _opted_out(node):
                continue
            parents = parents or PyParents.from_tree(tree)
            if not parents.in_security_context(node):
                continue
            findings.append(
                self._make_finding(
                    node=node,
                    filename=filename,
                    description=(
                        f"{algo.upper()} protects what looks like a security value. MD5 and "
                        "SHA-1 are broken for security: collisions are practical and both are "
                        "fast enough to brute-force passwords."
                    ),
                    fix_suggestion=_FIX,
                    confidence=0.7,
                )
            )
        return findings


def _weak_algorithm(call: ast.Call, imports: ImportMap) -> str | None:
    module, name = imports.resolve_call(call.func)
    if module != "hashlib" or name is None:
        return None
    if name in _WEAK:
        return name
    if name == "new" and call.args:
        first = call.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            algo = first.value.lower().replace("-", "")
            return algo if algo in _WEAK else None
    return None


def _opted_out(call: ast.Call) -> bool:
    return any(
        kw.arg == "usedforsecurity"
        and isinstance(kw.value, ast.Constant)
        and kw.value.value is False
        for kw in call.keywords
    )


REGISTRY.register(WeakHashRule())
