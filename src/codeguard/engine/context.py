# SPDX-License-Identifier: Apache-2.0
"""``RuleContext`` -- everything a rule needs to analyse one file."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from codeguard.lang.base import Language, LanguageSupport
from codeguard.lang.node import SourceNode


@dataclass
class RuleContext:
    """Per-file analysis context handed to :meth:`~codeguard.engine.rule.Rule.analyze`.

    Attributes
    ----------
    filename:
        Path (or ``"<stdin>"``) the source came from.
    source:
        Raw source text.
    language:
        The detected :class:`~codeguard.lang.base.Language`.
    lang:
        The parser backend for *language* (for structural ``query()`` access).
    root:
        The parsed tree as a uniform :class:`~codeguard.lang.node.SourceNode`.
    dataflow:
        Reserved for the intraprocedural taint pass (a later milestone); always
        ``None`` today.
    """

    filename: str
    source: str
    language: Language
    lang: LanguageSupport
    root: SourceNode
    dataflow: None = None
    _lines: list[str] | None = field(default=None, repr=False, compare=False)

    @property
    def lines(self) -> list[str]:
        """Source split into lines, cached."""
        if self._lines is None:
            self._lines = self.source.splitlines()
        return self._lines

    @property
    def python_ast(self) -> ast.Module:
        """The native :class:`ast.Module` for a Python file.

        Raises
        ------
        TypeError
            If this context is not for Python source.
        """
        node = self.root.native
        if not isinstance(node, ast.Module):
            raise TypeError(f"python_ast requested for a {self.language.value} context")
        return node
