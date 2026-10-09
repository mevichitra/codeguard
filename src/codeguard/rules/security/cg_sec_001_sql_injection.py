# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-001 — SQL query built with string formatting.

Detects f-strings, %-formatting, .format(), and string concatenation used
as the first argument to cursor.execute() / executemany() / executescript().

Why this matters
----------------
Building SQL queries by interpolating variables into strings is the textbook
SQL injection vector (CWE-89, OWASP A03:2021).  AI models produce this pattern
frequently because it is syntactically simple and mirrors common tutorial code.

The fix is always the same: use parameterized queries.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules._pysinks import is_dynamic_string, is_sql_execute

_FIX = (
    "Use parameterized queries instead of string interpolation: "
    'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
)


class SQLStringFormattingRule(AstRule):
    """Detect SQL queries built via string formatting."""

    id = "CG-SEC-001"
    title = "SQL query built with string formatting"
    description = (
        "The SQL query passed to execute() is constructed using string interpolation "
        "(f-string, %-format, .format(), or concatenation). This allows SQL injection "
        "if any interpolated value originates from user input."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    cwe = "CWE-89"
    owasp = "A03:2021 - Injection"

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        """Walk the AST looking for execute()/executemany() calls with dynamic SQL."""
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not is_sql_execute(node):
                continue
            if node.args and is_dynamic_string(node.args[0]):
                findings.append(
                    self._make_finding(
                        node=node,
                        filename=filename,
                        fix_suggestion=_FIX,
                    )
                )

        return findings


REGISTRY.register(SQLStringFormattingRule())
