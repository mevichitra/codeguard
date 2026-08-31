# SPDX-License-Identifier: Apache-2.0
"""Inline and file-level suppression comments.

    # codeguard: ignore[CG-SEC-001] reason: the value is a constant
    # codeguard: ignore[CG-SEC-001] reason: validated upstream  until=2026-12-31
    # codeguard: ignore-file[CG-SEC-002] reason: this module generates fixtures

The comment leader is ``#`` for Python, ``//`` for JavaScript / TypeScript.

Every suppression should carry a ``reason:``.  One without a reason still
suppresses, but the runner also raises **CG-META-001**.  An expired
``until=`` suppression stops suppressing and raises **CG-META-002**.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

META_MISSING_REASON = "CG-META-001"
META_EXPIRED = "CG-META-002"

_KEYWORD = r"(ignore|ignore-file|disable)"
_LINE_RE = re.compile(rf"(?:#|//)\s*codeguard:\s*{_KEYWORD}\[([^\]]+)\](?P<rest>.*)$")
_UNTIL_RE = re.compile(r"until=(\d{4}-\d{2}-\d{2})")
_REASON_RE = re.compile(r"reason:\s*(?P<reason>.*?)(?:\s+until=\d{4}-\d{2}-\d{2}|\s*$)")


@dataclass(frozen=True)
class Suppression:
    """One parsed suppression comment."""

    rule_ids: frozenset[str]
    reason: str | None
    until: date | None
    file_level: bool
    line: int  # 1-indexed line of the comment (== target line for inline)
    raw: str

    def covers(self, rule_id: str) -> bool:
        return rule_id in self.rule_ids

    def is_expired(self, today: date) -> bool:
        return self.until is not None and today > self.until


@dataclass
class SuppressionSet:
    """All suppressions found in one source file."""

    inline: dict[int, list[Suppression]] = field(default_factory=dict)
    file_level: list[Suppression] = field(default_factory=list)

    @classmethod
    def parse(cls, source: str) -> SuppressionSet:
        out = cls()
        for lineno, text in enumerate(source.splitlines(), start=1):
            match = _LINE_RE.search(text)
            if not match:
                continue
            keyword, ids_raw = match.group(1), match.group(2)
            rest = match.group("rest")
            until = None
            if (u := _UNTIL_RE.search(rest)) is not None:
                try:
                    until = date.fromisoformat(u.group(1))
                except ValueError:
                    until = None
            reason = None
            if (r := _REASON_RE.search(rest)) is not None:
                candidate = r.group("reason").strip()
                reason = candidate or None
            supp = Suppression(
                rule_ids=frozenset(i.strip() for i in ids_raw.split(",") if i.strip()),
                reason=reason,
                until=until,
                file_level=keyword in ("ignore-file", "disable"),
                line=lineno,
                raw=text.strip(),
            )
            if supp.file_level:
                out.file_level.append(supp)
            else:
                out.inline.setdefault(lineno, []).append(supp)
        return out

    def all(self) -> list[Suppression]:
        return [s for group in self.inline.values() for s in group] + self.file_level

    def _candidates(self, rule_id: str, line: int) -> list[Suppression]:
        found = [s for s in self.inline.get(line, []) if s.covers(rule_id)]
        found += [s for s in self.file_level if s.covers(rule_id)]
        return found

    def outcome(self, rule_id: str, line: int, today: date) -> tuple[str, Suppression] | None:
        """Decide what a finding's suppression comment does.

        - ``("suppress", s)``  -- an active suppression applies
        - ``("expired", s)``   -- only an expired suppression applies (does NOT suppress)
        - ``None``             -- no suppression comment covers this finding
        """
        candidates = self._candidates(rule_id, line)
        if not candidates:
            return None
        active = [s for s in candidates if not s.is_expired(today)]
        if active:
            return "suppress", active[0]
        return "expired", candidates[0]
