# SPDX-License-Identifier: Apache-2.0
"""Parent links for Python ``ast`` trees: loops, enclosing functions, binding names.

``ast`` nodes have no parent pointer.  :class:`PyParents` builds the map once
per file so rules can ask "is this call inside a loop?" or "what name is this
value assigned to?" without re-walking the tree.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass, field

LOOP_TYPES = (ast.For, ast.AsyncFor, ast.While)
SCOPE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)

#: Names that mark a value as security-sensitive (tokens, secrets, ids, ...).
SECURITY_WORD = re.compile(
    r"(?i)(token|secret|password|passwd|pwd|nonce|salt|otp|api_?key|private_?key|"
    r"session|csrf|verification|reset_?code|auth|credential|signature|hmac)"
)


@dataclass
class PyParents:
    """``id(child) -> parent`` for every node in one tree."""

    _parent: dict[int, ast.AST] = field(default_factory=dict)

    @classmethod
    def from_tree(cls, tree: ast.AST) -> PyParents:
        out = cls()
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                out._parent[id(child)] = node
        return out

    def parent(self, node: ast.AST) -> ast.AST | None:
        return self._parent.get(id(node))

    def ancestors(self, node: ast.AST) -> Iterator[ast.AST]:
        current = self.parent(node)
        while current is not None:
            yield current
            current = self.parent(current)

    def enclosing_loop(self, node: ast.AST) -> ast.For | ast.AsyncFor | ast.While | None:
        """The nearest loop whose **body** contains *node*, not crossing a def/class.

        A node in the loop's ``iter`` / ``test`` expression or its ``else`` block
        does not count: it runs once (``iter``) or after the loop.
        """
        child = node
        for anc in self.ancestors(node):
            if isinstance(anc, SCOPE_TYPES):
                return None
            if isinstance(anc, LOOP_TYPES) and any(child is stmt for stmt in anc.body):
                return anc
            child = anc
        return None

    def in_loop(self, node: ast.AST) -> bool:
        return self.enclosing_loop(node) is not None

    def enclosing_function(self, node: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        for anc in self.ancestors(node):
            if isinstance(anc, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return anc
        return None

    def binding_names(self, node: ast.AST, *, depth: int = 6) -> list[str]:
        """Names that give *node* meaning: assignment targets, keyword names,
        dict keys, ``return`` in a function -- nearest first, plus the enclosing
        function's name."""
        names: list[str] = []
        child = node
        for i, anc in enumerate(self.ancestors(node)):
            if i >= depth or isinstance(anc, (ast.ClassDef, ast.Module)):
                break
            if isinstance(anc, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets: list[ast.expr] = (
                    list(anc.targets) if isinstance(anc, ast.Assign) else [anc.target]
                )
                names.extend(_target_names(targets))
            elif isinstance(anc, ast.keyword) and anc.arg:
                names.append(anc.arg)
            elif isinstance(anc, ast.Dict):
                for k, v in zip(anc.keys, anc.values, strict=True):
                    if v is child and isinstance(k, ast.Constant) and isinstance(k.value, str):
                        names.append(k.value)
            elif isinstance(anc, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.append(anc.name)
                break
            child = anc
        return names

    def in_security_context(self, node: ast.AST) -> bool:
        """True if any binding name around *node* reads like a secret / token / id."""
        return any(SECURITY_WORD.search(name) for name in self.binding_names(node))


def _target_names(targets: list[ast.expr]) -> list[str]:
    out: list[str] = []
    for t in targets:
        if isinstance(t, ast.Name):
            out.append(t.id)
        elif isinstance(t, ast.Attribute):
            out.append(t.attr)
        elif isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant):
            out.append(str(t.slice.value))
        elif isinstance(t, (ast.Tuple, ast.List)):
            out.extend(_target_names(list(t.elts)))
    return out


def source_text(source: str, node: ast.AST) -> str:
    """The exact source of *node* (empty string if unavailable)."""
    return ast.get_source_segment(source, node) or ""
