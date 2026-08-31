# SPDX-License-Identifier: Apache-2.0
"""``SourceNode`` -- the uniform tree node handed to rules.

A rule that targets a single language may reach through to the parser-native
node via :attr:`SourceNode.native` (an :class:`ast.AST` for Python).  Rules that
span languages should stick to the wrapper's own API (:meth:`walk`,
:meth:`children`, :meth:`text`, :attr:`kind`).
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property

from .base import Language, Position


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
        """A normalized node-type name (e.g. ``"call"``, ``"assignment"``).

        For the ``ast`` backend this is the lower-cased class name; the
        normalization table grows as structural rules need it.
        """
        if isinstance(self.native, ast.AST):
            return type(self.native).__name__.lower()
        return type(self.native).__name__

    # ------------------------------------------------------------------
    # Position (1-indexed line and column)
    # ------------------------------------------------------------------

    @cached_property
    def start(self) -> Position:
        node = self.native
        if isinstance(node, ast.AST):
            line = getattr(node, "lineno", 1)
            col = getattr(node, "col_offset", 0)
            return Position(line=max(line, 1), col=col + 1)
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
        return None

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def text(self) -> str:
        """The source slice this node spans (best effort)."""
        if isinstance(self.native, ast.AST):
            segment = ast.get_source_segment(self.source, self.native)
            return segment if segment is not None else ""
        return ""

    def children(self) -> list[SourceNode]:
        if isinstance(self.native, ast.AST):
            return [
                SourceNode(native=c, language=self.language, source=self.source)
                for c in ast.iter_child_nodes(self.native)
            ]
        return []

    def walk(self) -> Iterator[SourceNode]:
        """Yield this node and every descendant, pre-order."""
        if isinstance(self.native, ast.AST):
            for n in ast.walk(self.native):
                yield SourceNode(native=n, language=self.language, source=self.source)
        else:
            yield self
