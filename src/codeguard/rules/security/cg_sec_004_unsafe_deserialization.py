# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-004 — Unsafe deserialization via pickle or yaml.load.

Detects:
  - ``pickle.loads(...)`` / ``pickle.load(...)``
  - ``_pickle.loads(...)`` (CPython internal alias)
  - ``marshal.loads(...)``
  - ``yaml.load(...)`` without ``Loader=SafeLoader`` (or ``Loader=yaml.SafeLoader``)

Why this matters
----------------
Deserializing data from untrusted sources using pickle or unsafe yaml is a
critical vulnerability (CWE-502, OWASP A08:2021).  Pickle can execute
arbitrary Python during deserialization; yaml.load() with the default
(FullLoader or older unsafe Loader) can instantiate arbitrary Python objects.

AI models commonly generate ``pickle.loads(data)`` and ``yaml.load(config)``
because the documentation examples often omit the Loader parameter.

False-positive guidance
-----------------------
``pickle.loads`` on *internally-generated, trusted* data is still risky (any
attacker who can modify your data store gets RCE) but you can suppress if
you've audited the data provenance:
``# codeguard: ignore[CG-SEC-004]``

``yaml.load`` with ``Loader=yaml.SafeLoader`` or ``Loader=SafeLoader`` is safe
and will NOT be flagged.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule

# (module, method) pairs that are always unsafe
_UNSAFE_CALLS: frozenset[tuple[str, str]] = frozenset(
    {
        ("pickle", "loads"),
        ("pickle", "load"),
        ("_pickle", "loads"),
        ("_pickle", "load"),
        ("marshal", "loads"),
        ("marshal", "load"),
    }
)

_SAFE_LOADERS = frozenset({"SafeLoader", "CSafeLoader"})

_FIX_PICKLE = (
    "Never unpickle data from untrusted sources. "
    "Consider JSON, msgpack, or protobuf for cross-process serialization."
)

_FIX_YAML = (
    "Pass Loader=yaml.SafeLoader: yaml.load(data, Loader=yaml.SafeLoader), "
    "or use yaml.safe_load(data)."
)


class UnsafeDeserializationRule(AstRule):
    """Detect pickle.loads, marshal.loads, and yaml.load without SafeLoader."""

    id = "CG-SEC-004"
    title = "Unsafe deserialization"
    description = (
        "Deserializing data with pickle, marshal, or yaml.load (without SafeLoader) "
        "can execute arbitrary code if the data source is attacker-controlled."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    cwe = "CWE-502"
    owasp = "A08:2021 - Software and Data Integrity Failures"

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        """Find unsafe deserialization calls."""
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            module, method = self._call_parts(node)
            if not module or not method:
                continue

            # pickle.loads / marshal.loads — always unsafe
            if (module, method) in _UNSAFE_CALLS:
                findings.append(
                    self._make_finding(
                        node=node,
                        filename=filename,
                        description=(
                            f"{module}.{method}() deserializes arbitrary Python objects. "
                            "This is a critical vulnerability if the data is attacker-controlled."
                        ),
                        fix_suggestion=_FIX_PICKLE,
                    )
                )

            # yaml.load — only unsafe without SafeLoader
            elif module == "yaml" and method == "load":
                if not self._has_safe_loader(node):
                    findings.append(
                        self._make_finding(
                            node=node,
                            filename=filename,
                            description=(
                                "yaml.load() without Loader=SafeLoader can instantiate "
                                "arbitrary Python objects from the YAML input."
                            ),
                            fix_suggestion=_FIX_YAML,
                        )
                    )

        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _call_parts(node: ast.Call) -> tuple[str, str]:
        """Return (module, method) for ``module.method(...)`` calls, else ('', '')."""
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if isinstance(node.func.value, ast.Name):
                return node.func.value.id, attr
        return "", ""

    @staticmethod
    def _has_safe_loader(node: ast.Call) -> bool:
        """Return True if Loader=SafeLoader (or equivalent) is present."""
        # Keyword argument: yaml.load(data, Loader=yaml.SafeLoader)
        for kw in node.keywords:
            if kw.arg == "Loader":
                val = kw.value
                loader_name = (
                    val.attr
                    if isinstance(val, ast.Attribute)
                    else (val.id if isinstance(val, ast.Name) else "")
                )
                if loader_name in _SAFE_LOADERS:
                    return True

        # Positional argument: yaml.load(data, yaml.SafeLoader)
        if len(node.args) >= 2:
            arg = node.args[1]
            loader_name = (
                arg.attr
                if isinstance(arg, ast.Attribute)
                else (arg.id if isinstance(arg, ast.Name) else "")
            )
            if loader_name in _SAFE_LOADERS:
                return True

        return False


REGISTRY.register(UnsafeDeserializationRule())
