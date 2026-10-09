# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-007 -- TLS certificate verification disabled.

- ``requests`` / ``httpx`` calls and clients with ``verify=False``
- ``aiohttp`` with ``ssl=False`` / ``verify_ssl=False``
- ``ssl._create_unverified_context()``
- ``ctx.verify_mode = ssl.CERT_NONE`` and ``ctx.check_hostname = False``

Without verification any network attacker can impersonate the server.  CWE-295.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules._pyimports import ImportMap

_HTTP_MODULES = frozenset({"requests", "httpx", "aiohttp", "urllib3"})
_HTTP_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "request", "stream", "send"}
)
_CLIENT_HINTS = ("session", "client", "http", "api", "conn")
_FALSE_KWARGS = frozenset({"verify", "verify_ssl", "ssl"})
_FIX = (
    "Keep certificate verification on. To trust a private CA, pass its bundle: "
    "requests.get(url, verify='/path/to/ca.pem') or ssl.create_default_context(cafile=...)."
)


class TlsVerificationDisabledRule(AstRule):
    id = "CG-SEC-007"
    title = "TLS certificate verification disabled"
    description = (
        "Certificate verification is turned off, so the connection accepts any "
        "certificate. Anyone on the network path can read and modify the traffic."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    cwe = "CWE-295"
    owasp = "A07:2021 - Identification and Authentication Failures"

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        imports = ImportMap.from_tree(tree)
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and self._call_disables(node, imports):
                findings.append(
                    self._make_finding(node=node, filename=filename, fix_suggestion=_FIX)
                )
            elif isinstance(node, ast.Assign) and self._assign_disables(node, imports):
                findings.append(
                    self._make_finding(node=node, filename=filename, fix_suggestion=_FIX)
                )
        return findings

    @staticmethod
    def _call_disables(call: ast.Call, imports: ImportMap) -> bool:
        module, name = imports.resolve_call(call.func)
        if (module, name) == ("ssl", "_create_unverified_context"):
            return True
        false_kw = any(
            kw.arg in _FALSE_KWARGS
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is False
            for kw in call.keywords
        )
        if not false_kw:
            return False
        top = (module or "").split(".")[0]
        if top in _HTTP_MODULES:
            return True
        func = call.func
        if isinstance(func, ast.Attribute) and func.attr in _HTTP_METHODS:
            receiver = ast.unparse(func.value).lower()
            return any(hint in receiver for hint in _CLIENT_HINTS)
        return False

    @staticmethod
    def _assign_disables(node: ast.Assign, imports: ImportMap) -> bool:
        value = node.value
        for target in node.targets:
            if not isinstance(target, ast.Attribute):
                continue
            if target.attr == "check_hostname":
                return isinstance(value, ast.Constant) and value.value is False
            if target.attr == "verify_mode":
                return _is_cert_none(value, imports)
        return False


def _is_cert_none(value: ast.expr, imports: ImportMap) -> bool:
    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
        base = value.value.id
        return value.attr == "CERT_NONE" and imports.module_aliases.get(base) == "ssl"
    if isinstance(value, ast.Name):
        return imports.symbol_imports.get(value.id) == ("ssl", "CERT_NONE")
    return False


REGISTRY.register(TlsVerificationDisabledRule())
