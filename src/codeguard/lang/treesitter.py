# SPDX-License-Identifier: Apache-2.0
"""Base class for tree-sitter-backed language support."""

from __future__ import annotations

from abc import abstractmethod
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import LanguageSupport, ParseResult, SyntaxErrorInfo
from .node import SourceNode

if TYPE_CHECKING:
    import tree_sitter

_QUERY_DIR = Path(__file__).parent / "queries"


class TreeSitterSupport(LanguageSupport):
    """Parse a language with tree-sitter.

    Subclasses supply :meth:`_ts_language`.  The parser and any ``.scm`` queries
    are created lazily and cached, so a scan that never touches this language
    never imports ``tree_sitter``.
    """

    comment_prefixes = ("//", "/*")

    def __init__(self) -> None:
        self._parser: tree_sitter.Parser | None = None
        self._queries: dict[str, Any] = {}

    @abstractmethod
    def _ts_language(self) -> tree_sitter.Language:
        """Return the compiled tree-sitter grammar for this language."""

    @property
    def _parser_obj(self) -> tree_sitter.Parser:
        if self._parser is None:
            import tree_sitter

            self._parser = tree_sitter.Parser(self._ts_language())
        return self._parser

    def parse(self, source: str, filename: str) -> ParseResult:
        tree = self._parser_obj.parse(source.encode("utf-8"))
        root = tree.root_node

        # tree-sitter is error-recovering: a stray token deep in the file still
        # yields a usable tree.  Only bail if nothing meaningful parsed.
        meaningful = [c for c in root.children if c.type not in ("ERROR", "comment")]
        if root.has_error and not meaningful:
            err = _first_error(root)
            return ParseResult(
                root=None,
                ok=False,
                error=SyntaxErrorInfo(
                    message="could not parse",
                    line=(err.start_point[0] + 1) if err else None,
                    col=(err.start_point[1] + 1) if err else None,
                ),
            )

        node = SourceNode(native=root, language=self.language, source=source)
        return ParseResult(root=node, ok=True)

    def query(self, name: str) -> Any | None:
        if name in self._queries:
            return self._queries[name]
        path = _QUERY_DIR / self.language.value / f"{name}.scm"
        if not path.is_file():
            self._queries[name] = None
            return None
        import tree_sitter

        compiled = tree_sitter.Query(self._ts_language(), path.read_text(encoding="utf-8"))
        self._queries[name] = compiled
        return compiled


def _first_error(node: tree_sitter.Node) -> tree_sitter.Node | None:
    stack = [node]
    while stack:
        n = stack.pop()
        if n.is_error or n.is_missing:
            return n
        stack.extend(n.children)
    return None


@cache
def _load_language(module_name: str, func_name: str) -> tree_sitter.Language:
    import importlib

    import tree_sitter

    mod = importlib.import_module(module_name)
    return tree_sitter.Language(getattr(mod, func_name)())
