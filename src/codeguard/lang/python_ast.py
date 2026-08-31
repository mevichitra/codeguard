# SPDX-License-Identifier: Apache-2.0
"""Python language support, backed by the standard library :mod:`ast`."""

from __future__ import annotations

import ast

from .base import Language, LanguageSupport, ParseResult, SyntaxErrorInfo
from .node import SourceNode


class PythonAstSupport(LanguageSupport):
    """Parse Python with :func:`ast.parse`."""

    language = Language.PYTHON
    extensions = (".py", ".pyi")
    comment_prefixes = ("#",)

    def parse(self, source: str, filename: str) -> ParseResult:
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as exc:
            return ParseResult(
                root=None,
                ok=False,
                error=SyntaxErrorInfo(message=exc.msg, line=exc.lineno, col=exc.offset),
            )
        root = SourceNode(native=tree, language=Language.PYTHON, source=source)
        return ParseResult(root=root, ok=True)
