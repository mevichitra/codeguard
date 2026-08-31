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
