# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-008 -- ``tempfile.mktemp()``.

``mktemp`` returns a name without creating the file.  Another process can
create (or symlink) that path first, so the program writes where an attacker
chose.  Deprecated since Python 2.3.  CWE-377.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules._pyimports import ImportMap

_FIX = (
    "Create the file atomically: tempfile.NamedTemporaryFile(delete=False), "
    "tempfile.mkstemp(), or tempfile.mkdtemp() for a private directory."
)


class InsecureTempfileRule(AstRule):
    id = "CG-SEC-008"
    title = "Insecure temporary file name (tempfile.mktemp)"
    description = (
        "tempfile.mktemp() returns a file name without creating the file. Between the "
        "call and the open, another process can create or symlink that path (a race)."
    )
    severity = Severity.MEDIUM
    category = Category.SECURITY
    cwe = "CWE-377"
    owasp = "A01:2021 - Broken Access Control"

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        imports = ImportMap.from_tree(tree)
        return [
            self._make_finding(node=node, filename=filename, fix_suggestion=_FIX)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and imports.resolve_call(node.func) == ("tempfile", "mktemp")
        ]


REGISTRY.register(InsecureTempfileRule())
