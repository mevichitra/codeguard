# SPDX-License-Identifier: Apache-2.0
"""Resolve call targets through Python import aliases.

Rules that match ``module.function(...)`` calls need to see through the ways an
import can rename things::

    import subprocess as sp        # sp.run(...)      -> ("subprocess", "run")
    from subprocess import run     # run(...)         -> ("subprocess", "run")
    from os import system as sh    # sh(...)          -> ("os", "system")

:class:`ImportMap` builds these tables once per file; :meth:`ImportMap.resolve_call`
maps a call node to a canonical ``(module, name)`` pair.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class ImportMap:
    """Import aliases in one module."""

    #: local name -> canonical module  (``"sp"`` -> ``"subprocess"``)
    module_aliases: dict[str, str] = field(default_factory=dict)
    #: local name -> (canonical module, original attribute)
    symbol_imports: dict[str, tuple[str, str]] = field(default_factory=dict)

    @classmethod
    def from_tree(cls, tree: ast.AST) -> ImportMap:
        m = cls()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    m.module_aliases[alias.asname or alias.name] = alias.name
                    if alias.asname is None:  # `import os.path` also binds `os`
                        m.module_aliases.setdefault(top, top)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                for alias in node.names:
                    local = alias.asname or alias.name
                    m.symbol_imports[local] = (node.module, alias.name)
        return m

    def resolve_call(self, func: ast.expr) -> tuple[str | None, str | None]:
        """Return the canonical ``(module, name)`` a call's *func* refers to.

        - ``module.attr(...)`` -> ``(canonical_module, attr)``
        - a bare name bound by ``from module import name`` -> ``(module, name)``
        - any other bare name -> ``(None, name)``
        - anything else -> ``(None, None)``
        """
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            base = self.module_aliases.get(func.value.id, func.value.id)
            return base, func.attr
        if isinstance(func, ast.Name):
            if func.id in self.symbol_imports:
                return self.symbol_imports[func.id]
            return None, func.id
        return None, None

    def has_module(self, module: str) -> bool:
        """True if ``import <module>`` (under any alias) appears in the file."""
        return module in self.module_aliases.values()

    def local_name_for(self, module: str) -> str | None:
        """The local name bound to ``import <module>`` (``"sp"`` for ``import x as sp``)."""
        if self.module_aliases.get(module) == module:
            return module
        for local, canonical in self.module_aliases.items():
            if canonical == module:
                return local
        return None


def insertion_line(tree: ast.Module) -> int:
    """The 1-indexed line where a new top-level ``import`` should go.

    After the last top-level import if there is one; otherwise after a module
    docstring and any ``from __future__`` imports; otherwise line 1.
    """
    last = 0
    body = tree.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        last = body[0].end_lineno or body[0].lineno
    for stmt in body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            last = stmt.end_lineno or stmt.lineno
        elif not (isinstance(stmt, ast.Expr) and stmt is body[0]):
            break
    return last + 1
