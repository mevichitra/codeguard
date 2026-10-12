# SPDX-License-Identifier: Apache-2.0
"""CG-PERF-002 -- string built with ``+=`` inside a loop.

Strings are immutable: each ``s += part`` may copy everything built so far,
which is quadratic in the final length.  Reported when the variable was
initialised to a string literal (or f-string) before the loop in the same
scope.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules._pyparents import PyParents

_FIX = "Collect the parts in a list and join once: parts.append(x); ... ''.join(parts)."


class StringConcatInLoopRule(AstRule):
    id = "CG-PERF-002"
    title = "String built with += inside a loop"
    description = (
        "Repeated `s += ...` on a string inside a loop can copy the whole string each "
        "time, which is quadratic in its final length."
    )
    severity = Severity.LOW
    category = Category.PERFORMANCE

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        parents = PyParents.from_tree(tree)
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.AugAssign)
                and isinstance(node.op, ast.Add)
                and isinstance(node.target, ast.Name)
            ):
                continue
            loop = parents.enclosing_loop(node)
            if loop is None:
                continue
            if _initialised_as_string(node.target.id, loop, tree, parents):
                findings.append(
                    self._make_finding(node=node, filename=filename, fix_suggestion=_FIX)
                )
        return findings


def _initialised_as_string(name: str, loop: ast.AST, tree: ast.AST, parents: PyParents) -> bool:
    scope = parents.enclosing_function(loop) or tree
    loop_line = getattr(loop, "lineno", 0)
    best: ast.Assign | ast.AnnAssign | None = None
    for node in ast.walk(scope):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.lineno >= loop_line:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(t, ast.Name) and t.id == name for t in targets) and (
            best is None or node.lineno > best.lineno
        ):
            best = node
    if best is None or best.value is None:
        return False
    value = best.value
    return isinstance(value, ast.JoinedStr) or (
        isinstance(value, ast.Constant) and isinstance(value.value, str)
    )


REGISTRY.register(StringConcatInLoopRule())
