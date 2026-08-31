# SPDX-License-Identifier: Apache-2.0
"""Core types for the language support layer."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass


class Language(str, enum.Enum):
    """A source language CodeGuard can parse."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


@dataclass(frozen=True)
class Position:
    """A 1-indexed ``(line, col)`` position.

    Both coordinates are 1-indexed to match editors, SARIF, and CodeGuard's
    :class:`~codeguard.engine.finding.Location`.  Parser-native offsets (``ast``
    and tree-sitter are both 0-indexed for columns) are converted at the
    boundary — rules never see a 0-indexed column.
    """

    line: int
    col: int

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError(f"line must be >= 1, got {self.line}")
        if self.col < 1:
            raise ValueError(f"col must be >= 1, got {self.col}")


@dataclass(frozen=True)
class SyntaxErrorInfo:
    """Where and why a parse failed."""

    message: str
    line: int | None = None
    col: int | None = None


@dataclass(frozen=True)
class ParseResult:
    """Outcome of :meth:`LanguageSupport.parse`.

    ``parse`` never raises for malformed input; it returns ``ok=False`` with an
    ``error`` instead, so the runner can skip a file and warn rather than crash.
    """

    root: object | None
    ok: bool
    error: SyntaxErrorInfo | None = None


class LanguageSupport(ABC):
    """Parser adapter for one :class:`Language`."""

    language: Language
    #: File extensions (with leading dot) this language claims.
    extensions: tuple[str, ...]
    #: Comment leaders used for inline suppression comments, longest first.
    comment_prefixes: tuple[str, ...]

    @abstractmethod
    def parse(self, source: str, filename: str) -> ParseResult:
        """Parse *source*.  Never raises; returns ``ok=False`` on failure."""

    def query(self, name: str) -> object | None:
        """Return a compiled structural query by name, or ``None``.

        Only meaningful for tree-sitter backends; the ``ast`` backend returns
        ``None`` and rules walk the tree directly.
        """
        return None
