# SPDX-License-Identifier: Apache-2.0
"""CG-PERF-005 -- regular expression compiled inside a loop.

``re.compile("...")`` or ``re.match("...", s)`` with a literal pattern inside a
loop body.  ``re`` caches compiled patterns, but every call still pays the
cache lookup and argument handling; hoisting a compiled pattern removes it.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules._pyimports import ImportMap
from codeguard.rules._pyparents import PyParents

_RE_FUNCS = frozenset(
    {"compile", "match", "search", "fullmatch", "sub", "subn", "findall", "finditer", "split"}
)
_FIX = "Compile once outside the loop: PATTERN = re.compile(r'...'), then PATTERN.search(s)."


class RegexInLoopRule(AstRule):
    id = "CG-PERF-005"
    title = "Regular expression compiled inside a loop"
    description = (
        "A regular expression with a constant pattern is compiled (or looked up in re's "
        "cache) on every iteration. Compile it once outside the loop."
    )
    severity = Severity.INFO
    category = Category.PERFORMANCE

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        imports = ImportMap.from_tree(tree)
        parents: PyParents | None = None
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            module, name = imports.resolve_call(node.func)
            if module != "re" or name not in _RE_FUNCS:
                continue
            pattern = node.args[0]
            if not (isinstance(pattern, ast.Constant) and isinstance(pattern.value, (str, bytes))):
                continue
            parents = parents or PyParents.from_tree(tree)
            if parents.in_loop(node):
                findings.append(
                    self._make_finding(node=node, filename=filename, fix_suggestion=_FIX)
                )
        return findings


REGISTRY.register(RegexInLoopRule())
