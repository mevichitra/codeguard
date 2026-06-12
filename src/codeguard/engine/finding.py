# SPDX-License-Identifier: Apache-2.0
"""Finding -- the atomic output unit of a CodeGuard analysis run."""

from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from typing import ClassVar


class Severity(str, enum.Enum):
    """Finding severity, in descending order of urgency."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    # Ordering: CRITICAL > HIGH > MEDIUM > LOW > INFO
    _order: ClassVar[list[str]] = ["critical", "high", "medium", "low", "info"]

    def __lt__(self, other: Severity) -> bool:  # type: ignore[override]
        return self._order.index(self.value) > other._order.index(other.value)  # type: ignore[attr-defined]

    def __le__(self, other: Severity) -> bool:  # type: ignore[override]
        return self == other or self < other

    def __gt__(self, other: Severity) -> bool:  # type: ignore[override]
        return other < self

    def __ge__(self, other: Severity) -> bool:  # type: ignore[override]
        return self == other or self > other


class Category(str, enum.Enum):
    """Rule category."""

    SECURITY = "security"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    AI_SMELL = "ai-smell"


@dataclass(frozen=True)
class Location:
    """Precise source location of a finding.

    Line and column numbers are 1-indexed to match what editors and SARIF expect.
    ``col`` is the start column; ``end_line`` / ``end_col`` are optional end positions.
    """

    file: str
    line: int
    col: int
    end_line: int | None = None
    end_col: int | None = None

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError(f"line must be ≥ 1, got {self.line}")
        if self.col < 0:
            raise ValueError(f"col must be ≥ 0, got {self.col}")


@dataclass(frozen=True)
class Finding:
    """A single diagnostic produced by a rule.

    ``rule_id`` is a stable public contract — it will never be renumbered.
    Tools, IDE plugins, and inline suppressions key on it.

    Attributes
    ----------
    rule_id:
        Stable rule identifier, e.g. ``CG-SEC-001``.
    title:
        Short (≤80 char) human-readable title.
    description:
        Full explanation of what was detected and why it matters.
    severity:
        How urgent this finding is.
    category:
        Broad category the rule belongs to.
    location:
        Where in the source the finding was detected.
    cwe:
        CWE identifier, e.g. ``CWE-89``.
    owasp:
        OWASP category reference, e.g. ``A03:2021 - Injection``.
    fix_suggestion:
        Actionable one-sentence fix. Optional but strongly encouraged.
    confidence:
        Detection confidence in [0.0, 1.0]. Rules must be honest.
        1.0 means the rule is certain; < 1.0 signals heuristic detection.
    suppressed:
        True when an inline ``# codeguard: ignore[RULE-ID]`` comment was found
        on the finding's line. Suppressed findings are still returned so callers
        can audit suppression usage.
    """

    rule_id: str
    title: str
    description: str
    severity: Severity
    category: Category
    location: Location
    cwe: str | None = None
    owasp: str | None = None
    fix_suggestion: str | None = None
    confidence: float = 1.0
    suppressed: bool = False

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("rule_id must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence!r}")

    def as_suppressed(self) -> Finding:
        """Return a copy of this finding with ``suppressed=True``."""
        return replace(self, suppressed=True)

    def to_dict(self) -> dict:  # type: ignore[type-arg]
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "location": {
                "file": self.location.file,
                "line": self.location.line,
                "col": self.location.col,
                "end_line": self.location.end_line,
                "end_col": self.location.end_col,
            },
            "cwe": self.cwe,
            "owasp": self.owasp,
            "fix_suggestion": self.fix_suggestion,
            "confidence": self.confidence,
            "suppressed": self.suppressed,
        }
