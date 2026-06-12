# SPDX-License-Identifier: Apache-2.0
"""Abstract base class for all CodeGuard rules."""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod

from .finding import Category, Finding, Location, Severity


class Rule(ABC):
    """Abstract base class that every CodeGuard rule must implement.

    Each rule detects exactly one concern.  Rules are self-contained:
    they receive a parsed AST and raw source, they return findings.
    They have no knowledge of other rules and no persistent state.

    To add a new rule, see CONTRIBUTING.md § "Adding a rule".

    Class attributes
    ----------------
    id:
        Stable rule identifier, e.g. ``CG-SEC-001``. Defined on the class,
        never on instances. Never renumber or reuse an ID.
    title:
        Short (≤ 80 char) human-readable title.
    description:
        Full explanation for developers who've never encountered this issue.
    severity:
        Default severity. Override per-finding via ``_make_finding`` if needed.
    category:
        Broad category — security, quality, performance, ai-smell.
    cwe:
        Primary CWE identifier, e.g. ``"CWE-89"``.  ``None`` if not applicable.
    owasp:
        OWASP category, e.g. ``"A03:2021 - Injection"``.  ``None`` if not applicable.
    """

    id: str
    title: str
    description: str
    severity: Severity
    category: Category
    cwe: str | None = None
    owasp: str | None = None

    @abstractmethod
    def check(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        """Analyse *tree* and return findings.

        Parameters
        ----------
        tree:
            ``ast.AST`` for the file.  Do **not** re-parse; use what you're given.
        source:
            Raw source text, available for line-level context if needed.
        filename:
            File path string — used when constructing :class:`~codeguard.engine.finding.Location`.

        Returns
        -------
        list[Finding]
            Empty list means no findings.  Never return ``None``.
        """

    # ------------------------------------------------------------------
    # Helpers for rule implementations
    # ------------------------------------------------------------------

    def _make_finding(
        self,
        *,
        node: ast.AST,
        filename: str,
        description: str | None = None,
        fix_suggestion: str | None = None,
        confidence: float = 1.0,
        severity: Severity | None = None,
    ) -> Finding:
        """Convenience factory — builds a :class:`Finding` from an AST node.

        Pulls ``lineno``, ``col_offset``, ``end_lineno``, ``end_col_offset``
        from *node* automatically.  All keyword arguments override the rule's
        class-level defaults when provided.
        """
        line: int = getattr(node, "lineno", 1)
        col: int = getattr(node, "col_offset", 0)
        end_line: int | None = getattr(node, "end_lineno", None)
        end_col: int | None = getattr(node, "end_col_offset", None)

        return Finding(
            rule_id=self.id,
            title=self.title,
            description=description or self.description,
            severity=severity if severity is not None else self.severity,
            category=self.category,
            location=Location(
                file=filename,
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
            ),
            cwe=self.cwe,
            owasp=self.owasp,
            fix_suggestion=fix_suggestion,
            confidence=confidence,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r})"
