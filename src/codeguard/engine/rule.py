# SPDX-License-Identifier: Apache-2.0
"""Abstract base classes for CodeGuard rules."""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod

from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode

from .context import RuleContext
from .finding import Category, Finding, Location, Severity


class Rule(ABC):
    """Abstract base class that every CodeGuard rule implements.

    Each rule detects exactly one concern.  Rules are self-contained: they
    receive a :class:`~codeguard.engine.context.RuleContext` and return findings.
    They have no knowledge of other rules and no persistent state.

    To add a new rule, see CONTRIBUTING.md § "Adding a rule".

    Class attributes
    ----------------
    id:
        Stable rule identifier, e.g. ``CG-SEC-001``.  Defined on the class,
        never on instances.  Never renumber or reuse an ID.
    title:
        Short (<= 80 char) human-readable title.
    description:
        Full explanation for developers who've never encountered this issue.
    severity:
        Default severity.  Override per-finding when needed.
    category:
        Broad category -- security, quality, performance, ai-smell.
    languages:
        The set of languages this rule can analyse.  The runner skips a rule
        for any file whose language is not in this set.
    cwe:
        Primary CWE identifier, e.g. ``"CWE-89"``.  ``None`` if not applicable.
    owasp:
        OWASP category, e.g. ``"A03:2021 - Injection"``.  ``None`` if not applicable.
    help_uri:
        Link to the rule's documentation page.  ``None`` falls back to a
        conventional URL derived from the rule ID.
    wants_dataflow:
        Opt in to the intraprocedural taint pass (a later milestone).  Ignored
        today.
    """

    id: str
    title: str
    description: str
    severity: Severity
    category: Category
    languages: frozenset[Language]
    cwe: str | None = None
    owasp: str | None = None
    help_uri: str | None = None
    wants_dataflow: bool = False

    @abstractmethod
    def analyze(self, ctx: RuleContext) -> list[Finding]:
        """Analyse the file described by *ctx* and return findings.

        Returns
        -------
        list[Finding]
            Empty list means no findings.  Never return ``None``.
        """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r})"


class AstRule(Rule):
    """Base class for Python rules that work directly on a :mod:`ast` tree.

    Subclasses implement :meth:`check_ast` with the same signature CodeGuard
    rules have always used.  This class adapts it to the language-aware
    :meth:`Rule.analyze` protocol and centralises the 0-indexed to 1-indexed
    column conversion in :meth:`_make_finding`.
    """

    languages = frozenset({Language.PYTHON})

    def analyze(self, ctx: RuleContext) -> list[Finding]:
        return self.check_ast(ctx.python_ast, ctx.source, ctx.filename)

    @abstractmethod
    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        """Analyse *tree* and return findings.

        Parameters
        ----------
        tree:
            ``ast.AST`` for the file.  Do **not** re-parse; use what you're given.
        source:
            Raw source text, available for line-level context if needed.
        filename:
            File path string -- used when constructing :class:`Location`.
        """

    # ------------------------------------------------------------------
    # Helper for rule implementations
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
        """Build a :class:`Finding` from an AST *node*.

        Pulls ``lineno`` / ``col_offset`` / ``end_lineno`` / ``end_col_offset``
        from *node* and converts the 0-indexed AST columns to CodeGuard's
        1-indexed :class:`Location` columns.
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
                line=max(line, 1),
                col=col + 1,
                end_line=end_line,
                end_col=None if end_col is None else end_col + 1,
            ),
            cwe=self.cwe,
            owasp=self.owasp,
            fix_suggestion=fix_suggestion,
            confidence=confidence,
        )


class TreeSitterRule(Rule):
    """Base class for rules over a tree-sitter tree (JavaScript / TypeScript).

    Subclasses set ``languages`` and implement :meth:`check_tree`, working with
    the uniform :class:`~codeguard.lang.node.SourceNode` API.
    """

    def analyze(self, ctx: RuleContext) -> list[Finding]:
        return self.check_tree(ctx.root, ctx)

    @abstractmethod
    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        """Analyse *root* (the file's tree) and return findings."""

    def _make_finding(
        self,
        *,
        node: SourceNode,
        ctx: RuleContext,
        description: str | None = None,
        fix_suggestion: str | None = None,
        confidence: float = 1.0,
        severity: Severity | None = None,
    ) -> Finding:
        """Build a :class:`Finding` from a :class:`SourceNode` (already 1-indexed)."""
        start = node.start
        end = node.end
        return Finding(
            rule_id=self.id,
            title=self.title,
            description=description or self.description,
            severity=severity if severity is not None else self.severity,
            category=self.category,
            location=Location(
                file=ctx.filename,
                line=start.line,
                col=start.col,
                end_line=end.line if end else None,
                end_col=end.col if end else None,
            ),
            cwe=self.cwe,
            owasp=self.owasp,
            fix_suggestion=fix_suggestion,
            confidence=confidence,
        )
