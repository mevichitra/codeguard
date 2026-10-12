# SPDX-License-Identifier: Apache-2.0
"""CG-PERF-004 -- redundant ``.keys()`` in iteration or membership.

``for k in d.keys()`` and ``k in d.keys()`` do the same as ``for k in d`` and
``k in d`` for any mapping, with an extra method call and view object.

Autofix (safe): drop ``.keys()`` when the receiver is a name or attribute.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Fix, Severity
from codeguard.engine.fixes import edit_for_ast_node
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules._pyparents import source_text


class RedundantKeysRule(AstRule):
    id = "CG-PERF-004"
    title = "Redundant .keys() in iteration or membership test"
    description = (
        "Iterating a mapping or testing membership already uses its keys; calling "
        ".keys() adds a method call and a view object for nothing."
    )
    severity = Severity.INFO
    category = Category.PERFORMANCE
    autofix = True

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        findings: list[Finding] = []
        for node in ast.walk(tree):
            candidates: list[ast.expr] = []
            if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                candidates.append(node.iter)
            elif isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], (ast.In, ast.NotIn)):
                    candidates.append(node.comparators[0])
            for call in candidates:
                receiver = _keys_receiver(call)
                if receiver is None:
                    continue
                text = source_text(source, receiver)
                if not text:
                    continue
                findings.append(
                    self._make_finding(
                        node=call,
                        filename=filename,
                        fix_suggestion=f"Use {text} directly.",
                        fix=Fix("Remove .keys()", (edit_for_ast_node(call, text),)),
                    )
                )
        return findings


def _keys_receiver(node: ast.expr) -> ast.expr | None:
    if (
        isinstance(node, ast.Call)
        and not node.args
        and not node.keywords
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "keys"
        and isinstance(node.func.value, (ast.Name, ast.Attribute))
    ):
        return node.func.value
    return None


REGISTRY.register(RedundantKeysRule())
