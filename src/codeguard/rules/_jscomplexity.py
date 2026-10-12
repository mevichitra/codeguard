# SPDX-License-Identifier: Apache-2.0
"""Function metrics for JavaScript / TypeScript over a tree-sitter :class:`SourceNode`."""

from __future__ import annotations

from collections.abc import Iterator

from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import FUNCTION_KINDS

_DECISIONS = frozenset(
    {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "switch_case",
        "catch_clause",
        "ternary_expression",
    }
)
_LOGICAL = frozenset({"&&", "||", "??"})


def functions(root: SourceNode) -> Iterator[SourceNode]:
    """Every function-like node in the tree, including nested ones."""
    for node in root.walk():
        if node.kind in FUNCTION_KINDS:
            yield node


def _own_nodes(fn: SourceNode) -> Iterator[SourceNode]:
    stack = list(reversed(fn.children()))
    while stack:
        node = stack.pop()
        yield node
        if node.kind in FUNCTION_KINDS or node.kind == "class_declaration":
            continue
        stack.extend(reversed(node.children()))


def cyclomatic(fn: SourceNode) -> int:
    """McCabe cyclomatic complexity of *fn* (nested functions excluded)."""
    score = 1
    for node in _own_nodes(fn):
        if node.kind in _DECISIONS:
            score += 1
        elif node.kind == "binary_expression":
            op = node.child_by_field("operator")
            if op is not None and op.text() in _LOGICAL:
                score += 1
    return score


def function_name(fn: SourceNode) -> str:
    """A readable name for *fn*: its declared name, or the binding it is assigned to."""
    name = fn.child_by_field("name")
    if name is not None:
        return name.text()
    from codeguard.rules._jsnodes import enclosing_binding_name

    return enclosing_binding_name(fn, depth=2) or "<anonymous>"
