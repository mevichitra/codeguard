# SPDX-License-Identifier: Apache-2.0
"""CG-PERF-001 -- membership test against a list / tuple literal inside a loop.

``x in [a, b, c]`` scans the sequence on every iteration; a set literal is a
hash lookup.  Reported for literals with at least ``min_elements`` items.

Autofix (safe): rewrite the literal as a set when every element is a hashable
constant (str / int / bytes / bool / None -- no floats, whose NaN and -0.0
compare differently) **and** the left operand is evidently hashable (a
literal, an f-string, ``str()`` / ``int()`` / ``len()`` / ``ord()`` /
``repr()``, or a string method such as ``.lower()``).  Anything else gets a
suggestion only, because ``unhashable in {...}`` raises ``TypeError``.
"""

from __future__ import annotations

import ast

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Fix, Severity
from codeguard.engine.fixes import edit_for_ast_node
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules._pyparents import PyParents, source_text

_HASHABLE_CALLS = frozenset({"str", "int", "len", "ord", "repr", "chr", "bool", "hash"})
_STR_METHODS = frozenset(
    {
        "lower",
        "upper",
        "strip",
        "lstrip",
        "rstrip",
        "casefold",
        "title",
        "capitalize",
        "removeprefix",
        "removesuffix",
        "decode",
        "encode",
    }
)


class ListMembershipInLoopRule(AstRule):
    id = "CG-PERF-001"
    title = "Membership test against a list literal inside a loop"
    description = (
        "`x in [...]` compares x against every element, on every iteration. A set "
        "literal `{...}` finds it with a single hash lookup."
    )
    severity = Severity.LOW
    category = Category.PERFORMANCE
    autofix = True
    default_options = {"min_elements": 3}  # noqa: RUF012

    def analyze(self, ctx: RuleContext) -> list[Finding]:
        return self._check(
            ctx.python_ast, ctx.source, ctx.filename, int(ctx.option("min_elements", 3))
        )

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        return self._check(tree, source, filename, 3)

    def _check(self, tree: ast.AST, source: str, filename: str, minimum: int) -> list[Finding]:
        parents: PyParents | None = None
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare) or len(node.ops) != 1:
                continue
            if not isinstance(node.ops[0], (ast.In, ast.NotIn)):
                continue
            seq = node.comparators[0]
            if not isinstance(seq, (ast.List, ast.Tuple)) or len(seq.elts) < minimum:
                continue
            if not all(isinstance(e, ast.Constant) for e in seq.elts):
                continue
            parents = parents or PyParents.from_tree(tree)
            if not parents.in_loop(node):
                continue
            fix = None
            if _all_hashable(seq.elts) and _evidently_hashable(node.left):
                items = ", ".join(source_text(source, e) for e in seq.elts)
                fix = Fix("Use a set literal", (edit_for_ast_node(seq, "{" + items + "}"),))
            findings.append(
                self._make_finding(
                    node=seq,
                    filename=filename,
                    fix_suggestion=(
                        "Use a set literal, or hoist a frozenset constant out of the loop."
                    ),
                    fix=fix,
                )
            )
        return findings


def _all_hashable(elts: list[ast.expr]) -> bool:
    return all(
        isinstance(e, ast.Constant)
        and (e.value is None or isinstance(e.value, (str, int, bytes, bool)))
        for e in elts
    )


def _evidently_hashable(node: ast.expr) -> bool:
    if isinstance(node, (ast.Constant, ast.JoinedStr)):
        return True
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id in _HASHABLE_CALLS:
            return True
        if isinstance(func, ast.Attribute) and func.attr in _STR_METHODS:
            return True
    return False


REGISTRY.register(ListMembershipInLoopRule())
