# SPDX-License-Identifier: Apache-2.0
"""CG-PERF-003 -- ``for i in range(len(seq))`` used to index ``seq``.

Iterating indices and then indexing does an extra lookup per item and is
harder to read than ``enumerate``.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule

_FIX = "Iterate directly: for item in seq, or for i, item in enumerate(seq)."


class RangeLenRule(AstRule):
    id = "CG-PERF-003"
    title = "for i in range(len(seq)) used to index seq"
    description = (
        "The loop iterates over indices only to look items up with seq[i]. Iterating the "
        "sequence directly (or with enumerate) avoids a lookup per item."
    )
    severity = Severity.INFO
    category = Category.PERFORMANCE

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.For, ast.AsyncFor)) or not isinstance(
                node.target, ast.Name
            ):
                continue
            seq = _range_len_target(node.iter)
            if seq is None:
                continue
            index = node.target.id
            if any(
                isinstance(n, ast.Subscript)
                and isinstance(n.value, ast.Name)
                and n.value.id == seq
                and isinstance(n.slice, ast.Name)
                and n.slice.id == index
                for stmt in node.body
                for n in ast.walk(stmt)
            ):
                findings.append(
                    self._make_finding(node=node.iter, filename=filename, fix_suggestion=_FIX)
                )
        return findings


def _range_len_target(it: ast.expr) -> str | None:
    if (
        isinstance(it, ast.Call)
        and isinstance(it.func, ast.Name)
        and it.func.id == "range"
        and len(it.args) == 1
        and isinstance(it.args[0], ast.Call)
        and isinstance(it.args[0].func, ast.Name)
        and it.args[0].func.id == "len"
        and len(it.args[0].args) == 1
        and isinstance(it.args[0].args[0], ast.Name)
    ):
        return it.args[0].args[0].id
    return None


REGISTRY.register(RangeLenRule())
