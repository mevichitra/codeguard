# SPDX-License-Identifier: Apache-2.0
"""Finding -- the atomic output unit of a CodeGuard analysis run."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, replace
from typing import Any

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


class Severity(str, enum.Enum):
    """Finding severity, in descending order of urgency."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    def __lt__(self, other: Severity) -> bool:  # type: ignore[override]
        return _SEVERITY_ORDER.index(self.value) > _SEVERITY_ORDER.index(other.value)

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
    META = "meta"


@dataclass(frozen=True)
class Location:
    """Precise source location of a finding.

    Line and column numbers are **1-indexed** to match what editors and SARIF
    expect.  ``col`` is the start column; ``end_line`` / ``end_col`` are optional
    end positions.
    """

    file: str
    line: int
    col: int
    end_line: int | None = None
    end_col: int | None = None

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError(f"line must be >= 1, got {self.line}")
        if self.col < 1:
            raise ValueError(f"col must be >= 1, got {self.col}")


@dataclass(frozen=True)
class TextEdit:
    """A single replacement in a source file, for an autofix.

    Positions use the same convention as :class:`Location`: 1-indexed lines and
    1-indexed columns counted in **UTF-8 bytes** (exactly what ``ast`` and
    tree-sitter report, plus one).  The end position is exclusive.  A
    zero-width edit (start == end) is an insertion.
    """

    start_line: int
    start_col: int
    end_line: int
    end_col: int
    replacement: str


@dataclass(frozen=True)
class Fix:
    """A suggested code change that resolves a finding.

    ``safe`` fixes preserve program semantics and are applied by
    ``codeguard scan --fix`` and the editor "Fix all" action.  The edits of one
    fix are applied atomically (all or none).
    """

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "safe": self.safe,
            "edits": [
                {
                    "start_line": e.start_line,
                    "start_col": e.start_col,
                    "end_line": e.end_line,
                    "end_col": e.end_col,
                    "replacement": e.replacement,
                }
                for e in self.edits
            ],
        }

    description: str
    edits: tuple[TextEdit, ...]
    safe: bool = True


@dataclass(frozen=True)
class RelatedLocation:
    """A secondary location that explains a finding (e.g. a taint source or hop)."""

    location: Location
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.location.file,
            "line": self.location.line,
            "col": self.location.col,
            "end_line": self.location.end_line,
            "end_col": self.location.end_col,
            "message": self.message,
        }


@dataclass(frozen=True)
class Triage:
    """A verdict on whether a finding is a true positive.

    Reserved for a post-2.0 offline triage layer; ``Finding.triage`` is always
    ``None`` today.
    """

    verdict: str  # "true" | "false" | "uncertain"
    rationale: str
    source: str  # "heuristic" | "offline-model" | "human"


@dataclass(frozen=True)
class Finding:
    """A single diagnostic produced by a rule.

    ``rule_id`` is a stable public contract -- it will never be renumbered.
    Tools, IDE plugins, and inline suppressions key on it.

    Attributes
    ----------
    rule_id:
        Stable rule identifier, e.g. ``CG-SEC-001``.
    title:
        Short (<= 80 char) human-readable title.
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
        Actionable one-sentence fix.  Optional but strongly encouraged.
    confidence:
        Detection confidence in ``[0.0, 1.0]``.  ``1.0`` means the rule is
        certain; ``< 1.0`` signals heuristic detection.
    suppressed:
        True when a ``# codeguard: ignore[RULE-ID]`` comment (or the file-level
        form) applied to this finding.  Suppressed findings are still returned so
        callers can audit suppression usage.
    fingerprint:
        Stable identity of this finding across reformatting and line moves,
        assigned by the runner.  Empty until assigned.
    fix:
        A suggested autofix, or ``None``.
    related:
        Secondary locations that explain the finding, e.g. where untrusted data
        entered and the assignments it flowed through.
    triage:
        A true/false-positive verdict, or ``None``.  Reserved for a later
        milestone.
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
    baselined: bool = False
    fingerprint: str = ""
    fix: Fix | None = field(default=None)
    triage: Triage | None = field(default=None)
    related: tuple[RelatedLocation, ...] = ()

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("rule_id must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence!r}")

    def as_suppressed(self) -> Finding:
        """Return a copy of this finding with ``suppressed=True``."""
        return replace(self, suppressed=True)

    def with_fingerprint(self, fingerprint: str) -> Finding:
        """Return a copy of this finding with ``fingerprint`` set."""
        return replace(self, fingerprint=fingerprint)

    def as_baselined(self) -> Finding:
        """Return a copy of this finding marked as present in the baseline."""
        return replace(self, baselined=True)

    def to_dict(self) -> dict[str, Any]:
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
            "baselined": self.baselined,
            "fingerprint": self.fingerprint,
            "fix": self.fix.to_dict() if self.fix is not None else None,
            "related": [r.to_dict() for r in self.related],
        }
