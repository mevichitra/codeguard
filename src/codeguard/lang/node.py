# SPDX-License-Identifier: Apache-2.0
"""``SourceNode`` -- the uniform tree node handed to rules.

A rule that targets a single language may reach through to the parser-native
node via :attr:`SourceNode.native` -- an :class:`ast.AST` for Python, a
``tree_sitter.Node`` for JavaScript / TypeScript.  Rules that span languages
should stick to the wrapper's own API (:meth:`walk`, :meth:`children`,
:meth:`child_by_field`, :meth:`text`, :attr:`kind`).
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property

from .base import Language, Position


def _is_ts_node(obj: object) -> bool:
    """Duck-type a tree_sitter.Node without importing tree_sitter."""
    return hasattr(obj, "type") and hasattr(obj, "start_point") and hasattr(obj, "children")


@dataclass(frozen=True)
class SourceNode:
    """A read-only wrapper over one parser node."""

    native: object
    language: Language
    source: str

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @cached_property
    def kind(self) -> str:
        """A normalized node-type name.

        ``ast`` backend: the lower-cased class name (``"call"``, ``"assign"``).
        tree-sitter backend: the grammar's node type (``"call_expression"``,
        ``"member_expression"``).
        """
        if isinstance(self.native, ast.AST):
            return type(self.native).__name__.lower()
        if _is_ts_node(self.native):
            return str(self.native.type)  # type: ignore[attr-defined]
        return type(self.native).__name__

    # ------------------------------------------------------------------
    # Position (1-indexed line and column)
    # ------------------------------------------------------------------

    @cached_property
    def start(self) -> Position:
        node = self.native
        if isinstance(node, ast.AST):
            return Position(
                line=max(getattr(node, "lineno", 1), 1),
                col=getattr(node, "col_offset", 0) + 1,
            )
        if _is_ts_node(node):
            row, col = node.start_point  # type: ignore[attr-defined]
            return Position(line=row + 1, col=col + 1)
        raise TypeError(f"start position unavailable for {node!r}")

    @cached_property
    def end(self) -> Position | None:
        node = self.native
        if isinstance(node, ast.AST):
            line = getattr(node, "end_lineno", None)
            col = getattr(node, "end_col_offset", None)
            if line is None or col is None:
                return None
            return Position(line=max(line, 1), col=col + 1)
        if _is_ts_node(node):
            row, col = node.end_point  # type: ignore[attr-defined]
            return Position(line=row + 1, col=col + 1)
        return None

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def _wrap(self, native: object) -> SourceNode:
        return SourceNode(native=native, language=self.language, source=self.source)

    def text(self) -> str:
        """The source slice this node spans (best effort)."""
        if isinstance(self.native, ast.AST):
            segment = ast.get_source_segment(self.source, self.native)
            return segment if segment is not None else ""
        if _is_ts_node(self.native):
            raw = self.native.text  # type: ignore[attr-defined]
            return raw.decode("utf-8", "replace") if raw is not None else ""
        return ""

    def children(self) -> list[SourceNode]:
        if isinstance(self.native, ast.AST):
            return [self._wrap(c) for c in ast.iter_child_nodes(self.native)]
        if _is_ts_node(self.native):
            return [self._wrap(c) for c in self.native.children]  # type: ignore[attr-defined]
        return []

    def child_by_field(self, name: str) -> SourceNode | None:
        """The named child (tree-sitter field), or ``None``.

        For the ``ast`` backend, *name* is an attribute name; a list-valued
        attribute yields its first element.
        """
        if _is_ts_node(self.native):
            child = self.native.child_by_field_name(name)  # type: ignore[attr-defined]
            return self._wrap(child) if child is not None else None
        if isinstance(self.native, ast.AST):
            value = getattr(self.native, name, None)
            if isinstance(value, ast.AST):
                return self._wrap(value)
            if isinstance(value, list) and value and isinstance(value[0], ast.AST):
                return self._wrap(value[0])
        return None

    def walk(self) -> Iterator[SourceNode]:
        """Yield this node and every descendant, pre-order."""
        if isinstance(self.native, ast.AST):
            for n in ast.walk(self.native):
                yield self._wrap(n)
            return
        if _is_ts_node(self.native):
            stack = [self.native]
            while stack:
                node = stack.pop()
                yield self._wrap(node)
                stack.extend(reversed(node.children))  # type: ignore[attr-defined]
            return
        yield self
