# SPDX-License-Identifier: Apache-2.0
"""``RuleContext`` -- everything a rule needs to analyse one file."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from codeguard.lang.base import Language, LanguageSupport
from codeguard.lang.node import SourceNode

from .dataflow.model import DataflowResult
from .text import split_lines

_NO_OPTIONS: Mapping[str, Any] = MappingProxyType({})


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
        The taint analysis for this file, computed once when any active rule
        sets ``wants_dataflow``.  ``None`` otherwise, or if the analysis failed.
    options:
        The current rule's options: its ``default_options`` overlaid with the
        project's ``[rules.<ID>]`` settings.  Set by the runner per rule.
    """

    filename: str
    source: str
    language: Language
    lang: LanguageSupport
    root: SourceNode
    dataflow: DataflowResult | None = None
    options: Mapping[str, Any] = field(default_factory=lambda: _NO_OPTIONS)
    _lines: list[str] | None = field(default=None, repr=False, compare=False)

    @property
    def lines(self) -> list[str]:
        """Source split into lines, cached."""
        if self._lines is None:
            self._lines = split_lines(self.source)
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

    def option(self, key: str, default: Any = None) -> Any:
        """Return the current rule's option *key*, or *default* if unset."""
        return self.options.get(key, default)
