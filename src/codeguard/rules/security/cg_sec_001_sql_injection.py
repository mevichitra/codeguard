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

from codeguard.engine.finding import Category, Finding, Location, RelatedLocation, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules._pyparents import PyParents
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
        parents: PyParents | None = None

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not is_sql_execute(node) or not node.args:
                continue
            query = node.args[0]
            if is_dynamic_string(query):
                parents = parents or PyParents.from_tree(tree)
                if not _concat_of_local_constants(query, node, tree, parents):
                    findings.append(
                        self._make_finding(node=node, filename=filename, fix_suggestion=_FIX)
                    )
                continue
            if isinstance(query, ast.Name):
                # `query = f"...{x}"` then `cursor.execute(query)`: one local hop.
                parents = parents or PyParents.from_tree(tree)
                built = _last_assignment(query.id, node, tree, parents)
                if built is not None and is_dynamic_string(built.value):
                    findings.append(
                        self._make_finding(
                            node=node,
                            filename=filename,
                            description=(
                                f"The SQL query in '{query.id}' (built on line {built.lineno}) "
                                "uses string interpolation. This allows SQL injection if any "
                                "interpolated value originates from user input."
                            ),
                            fix_suggestion=_FIX,
                            confidence=0.9,
                            related=(
                                RelatedLocation(
                                    Location(filename, built.lineno, built.col_offset + 1),
                                    f"Query string built here: {query.id} = ...",
                                ),
                            ),
                        )
                    )

        return findings


def _concat_of_local_constants(
    expr: ast.AST, call: ast.Call, tree: ast.AST, parents: PyParents
) -> bool:
    """True for ``"SELECT * FROM " + table`` where ``table = "users"`` just before."""
    if not (isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add)):
        return False

    def constant(node: ast.AST) -> bool:
        if isinstance(node, ast.Constant):
            return isinstance(node.value, str)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return constant(node.left) and constant(node.right)
        if isinstance(node, ast.Name):
            built = _last_assignment(node.id, call, tree, parents)
            return (
                built is not None
                and isinstance(built.value, ast.Constant)
                and isinstance(built.value.value, str)
            )
        return False

    return constant(expr)


def _last_assignment(
    name: str, call: ast.Call, tree: ast.AST, parents: PyParents
) -> ast.Assign | None:
    """The last ``name = ...`` before *call* in the same function (or module)."""
    scope: ast.AST = parents.enclosing_function(call) or tree
    best: ast.Assign | None = None
    for node in ast.walk(scope):
        if (
            isinstance(node, ast.Assign)
            and node.lineno < call.lineno
            and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
            and (parents.enclosing_function(node) or tree) is scope
            and (best is None or node.lineno > best.lineno)
        ):
            best = node
    return best


REGISTRY.register(SQLStringFormattingRule())
