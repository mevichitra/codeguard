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

_SQL_METHODS = frozenset({"execute", "executemany", "executescript"})

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
            if not self._is_sql_call(node):
                continue
            if node.args and self._is_dynamic_string(node.args[0]):
                findings.append(
                    self._make_finding(
                        node=node,
                        filename=filename,
                        fix_suggestion=_FIX,
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_sql_call(node: ast.Call) -> bool:
        """Return True if the call is a known SQL-execution method."""
        if isinstance(node.func, ast.Attribute):
            return node.func.attr in _SQL_METHODS
        return False

    @staticmethod
    def _is_dynamic_string(node: ast.AST) -> bool:
        """Return True if *node* produces a string via formatting or concatenation."""
        # f"SELECT ... {var} ..."
        if isinstance(node, ast.JoinedStr):
            return True
        # "SELECT ..." % var
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            return True
        # "SELECT ...".format(var)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
        ):
            return True
        # "SELECT " + var  or  var + " FROM ..."
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            # Only flag if at least one operand is not a literal
            left_literal = isinstance(node.left, ast.Constant)
            right_literal = isinstance(node.right, ast.Constant)
            return not (left_literal and right_literal)
        return False


REGISTRY.register(SQLStringFormattingRule())
