# SPDX-License-Identifier: Apache-2.0
"""Tests for the Python language backend and the SourceNode wrapper."""

from __future__ import annotations

import ast

from codeguard.lang import Language, PythonAstSupport, language_for_path, support_for
from codeguard.lang.node import SourceNode

SUPPORT = PythonAstSupport()


class TestParse:
    def test_ok(self) -> None:
        result = SUPPORT.parse("x = 1\n", "m.py")
        assert result.ok
        assert result.error is None
        assert isinstance(result.root, SourceNode)
        assert isinstance(result.root.native, ast.Module)

    def test_syntax_error_does_not_raise(self) -> None:
        result = SUPPORT.parse("def broken(\n", "m.py")
        assert not result.ok
        assert result.root is None
        assert result.error is not None
        assert result.error.line == 1

    def test_query_is_none_for_ast_backend(self) -> None:
        assert SUPPORT.query("anything") is None


class TestRegistry:
    def test_language_for_path(self) -> None:
        assert language_for_path("a/b/c.py") is Language.PYTHON
        assert language_for_path("a/b/c.pyi") is Language.PYTHON
        assert language_for_path("a/b/c.txt") is None

    def test_support_for(self) -> None:
        assert isinstance(support_for(Language.PYTHON), PythonAstSupport)


class TestSourceNode:
    def _root(self, src: str) -> SourceNode:
        result = SUPPORT.parse(src, "m.py")
        assert result.root is not None
        return result.root

    def test_kind_and_walk(self) -> None:
        root = self._root("value = compute(x)\n")
        kinds = {n.kind for n in root.walk()}
        assert "module" in kinds
        assert "call" in kinds
        assert "assign" in kinds

    def test_position_is_one_indexed(self) -> None:
        root = self._root("x = 1\nname = 2\n")
        names = [n for n in root.walk() if n.kind == "name" and n.text() == "name"]
        assert names
        assert names[0].start.line == 2
        assert names[0].start.col == 1  # 'ast' col_offset 0 -> 1-indexed

    def test_children_and_text(self) -> None:
        root = self._root("a + b\n")
        expr = root.children()[0]  # the Expr statement
        assert expr.kind == "expr"
        assert "a + b" in expr.text()
