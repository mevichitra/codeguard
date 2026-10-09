# SPDX-License-Identifier: Apache-2.0
"""Function metrics for Python: cyclomatic complexity, nesting depth, parameter count.

Nested function and class definitions are measured separately and never add to
their enclosing function's numbers.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef

_NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
_BRANCHES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.IfExp,
    ast.Assert,
    ast.match_case,
)
_NESTING: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.match_case,
)
if hasattr(ast, "TryStar"):  # Python 3.11+
    _NESTING = (*_NESTING, ast.TryStar)


def functions(tree: ast.AST) -> Iterator[FunctionNode]:
    """Every function and method in *tree*, including nested ones."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _own_nodes(fn: FunctionNode) -> Iterator[ast.AST]:
    """Nodes in *fn*'s body, not descending into nested defs, classes, or lambdas."""
    stack: list[ast.AST] = list(reversed(fn.body))
    while stack:
        node = stack.pop()
        if isinstance(node, _NESTED_SCOPES):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def cyclomatic(fn: FunctionNode) -> int:
    """McCabe cyclomatic complexity: 1 + number of decision points."""
    score = 1
    for node in _own_nodes(fn):
        if isinstance(node, _BRANCHES):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            score += 1 + len(node.ifs)
    return score


def max_nesting(fn: FunctionNode) -> int:
    """Deepest nesting of control-flow blocks inside *fn* (0 for a flat body)."""

    def depth(stmts: list[ast.stmt], level: int) -> int:
        best = level
        for stmt in stmts:
            if isinstance(stmt, _NESTED_SCOPES):
                continue
            inner = level + 1 if isinstance(stmt, _NESTING) else level
            for block in _blocks(stmt):
                best = max(best, depth(block, inner))
            if isinstance(stmt, ast.Match):
                for case in stmt.cases:
                    best = max(best, depth(case.body, level + 1))
        return best

    return depth(fn.body, 0)


def _blocks(stmt: ast.stmt) -> list[list[ast.stmt]]:
    blocks: list[list[ast.stmt]] = []
    for name in ("body", "orelse", "finalbody"):
        value = getattr(stmt, name, None)
        if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
            blocks.append(value)
    for handler in getattr(stmt, "handlers", []) or []:
        blocks.append(handler.body)
    return blocks


def param_count(fn: FunctionNode) -> int:
    """Number of parameters, not counting a leading ``self`` / ``cls``."""
    args = fn.args
    positional = [*args.posonlyargs, *args.args]
    if positional and positional[0].arg in ("self", "cls"):
        positional = positional[1:]
    count = len(positional) + len(args.kwonlyargs)
    count += 1 if args.vararg else 0
    count += 1 if args.kwarg else 0
    return count
