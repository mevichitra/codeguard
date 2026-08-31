# SPDX-License-Identifier: Apache-2.0
"""Meta rules -- emitted by the suppression engine, not by AST analysis.

CG-META-001 / CG-META-002 are registered here so ``list-rules`` and ``explain``
can describe them and so they can be disabled or remapped like any other rule.
The findings themselves are produced by
:class:`codeguard.engine.suppressions.SuppressionSet` via the runner.
"""

from __future__ import annotations

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import Rule
from codeguard.engine.suppressions import META_EXPIRED, META_MISSING_REASON
from codeguard.lang.base import Language

_ALL_LANGS = frozenset(Language)


class _MetaRule(Rule):
    severity = Severity.LOW
    category = Category.META
    languages = _ALL_LANGS

    def analyze(self, ctx: RuleContext) -> list[Finding]:
        return []  # emitted by the runner from parsed suppressions


class SuppressionMissingReasonRule(_MetaRule):
    id = META_MISSING_REASON
    title = "Suppression comment has no reason"
    description = (
        "A `# codeguard: ignore[...]` comment does not include `reason: ...`. "
        "Unexplained suppressions rot: require a short reason so reviewers know "
        "why the finding was waived."
    )
    help_uri = "https://mevichitra.github.io/codeguard/suppressions/"


class ExpiredSuppressionRule(_MetaRule):
    id = META_EXPIRED
    title = "Suppression has expired"
    description = (
        "A `# codeguard: ignore[...] until=YYYY-MM-DD` comment is past its date. "
        "The underlying finding is active again -- fix it, or renew the "
        "suppression with a new date and reason."
    )
    severity = Severity.MEDIUM
    help_uri = "https://mevichitra.github.io/codeguard/suppressions/"


REGISTRY.register(SuppressionMissingReasonRule())
REGISTRY.register(ExpiredSuppressionRule())
