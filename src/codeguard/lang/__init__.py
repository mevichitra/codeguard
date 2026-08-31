# SPDX-License-Identifier: Apache-2.0
"""Language support layer.

Each :class:`~codeguard.lang.base.LanguageSupport` implementation wraps a parser
for one language and hands rules a uniform :class:`~codeguard.lang.node.SourceNode`.
Rules declare which languages they target; the runner only invokes a rule for a
file whose language is in that set.

Python is backed by the standard library :mod:`ast`.  JavaScript and TypeScript
(added in a later milestone) are backed by tree-sitter.
"""

from __future__ import annotations

from .base import Language, LanguageSupport, ParseResult, Position, SyntaxErrorInfo
from .node import SourceNode
from .python_ast import PythonAstSupport
from .registry import LANGUAGES, language_for_path, support_for

__all__ = [
    "LANGUAGES",
    "Language",
    "LanguageSupport",
    "ParseResult",
    "Position",
    "PythonAstSupport",
    "SourceNode",
    "SyntaxErrorInfo",
    "language_for_path",
    "support_for",
]
