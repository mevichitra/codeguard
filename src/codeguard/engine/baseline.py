# SPDX-License-Identifier: Apache-2.0
"""Baseline files -- freeze the findings that exist today so CI only fails on new ones.

A baseline is a JSON file of finding fingerprints.  ``scan --baseline path`` marks
any finding whose fingerprint is in the file as ``baselined`` (excluded from the
exit code, still shown).  ``codeguard baseline create / update / prune`` manages
the file.

Fingerprints (see :mod:`codeguard.engine.fingerprint`) are stable across
reformatting and line moves, so a baselined finding stays matched as the file
around it changes -- and a genuinely new problem is not.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .finding import Finding

SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Baseline:
    """The contents of a baseline file."""

    fingerprints: dict[str, dict[str, str]] = field(default_factory=dict)
    tool_version: str = "0.0.0"
    created: str = field(default_factory=_now)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_findings(cls, findings: list[Finding], *, tool_version: str = "0.0.0") -> Baseline:
        b = cls(tool_version=tool_version)
        b._add(findings)
        return b

    @classmethod
    def load(cls, path: Path) -> Baseline:
        """Load a baseline file.  Raises ``ValueError`` on a malformed file."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path}: cannot read baseline: {exc}") from exc
        if not isinstance(data, dict) or "fingerprints" not in data:
            raise ValueError(f"{path}: not a CodeGuard baseline file")
        fps = data.get("fingerprints", {})
        if not isinstance(fps, dict):
            raise ValueError(f"{path}: 'fingerprints' must be an object")
        return cls(
            fingerprints={str(k): dict(v) for k, v in fps.items()},
            tool_version=str(data.get("tool_version", "0.0.0")),
            created=str(data.get("created", _now())),
        )

    # ------------------------------------------------------------------
    # Query / mutate
    # ------------------------------------------------------------------

    def __contains__(self, fingerprint: object) -> bool:
        return fingerprint in self.fingerprints

    def __len__(self) -> int:
        return len(self.fingerprints)

    def _add(self, findings: list[Finding]) -> None:
        for f in findings:
            if not f.fingerprint or f.fingerprint in self.fingerprints:
                continue
            self.fingerprints[f.fingerprint] = {
                "rule_id": f.rule_id,
                "file": f.location.file,
                "first_seen": _now(),
            }

    def updated_with(self, findings: list[Finding]) -> Baseline:
        """Return a copy with any new findings added (existing ``first_seen`` kept)."""
        out = Baseline(
            fingerprints=dict(self.fingerprints),
            tool_version=self.tool_version,
            created=self.created,
        )
        out._add(findings)
        return out

    def pruned(self, live_fingerprints: set[str]) -> Baseline:
        """Return a copy with entries that no longer correspond to a finding removed."""
        return Baseline(
            fingerprints={k: v for k, v in self.fingerprints.items() if k in live_fingerprints},
            tool_version=self.tool_version,
            created=self.created,
        )

    # ------------------------------------------------------------------
    # Serialise
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {
            "version": SCHEMA_VERSION,
            "created": self.created,
            "tool_version": self.tool_version,
            "fingerprints": dict(sorted(self.fingerprints.items())),
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")


def apply_baseline(findings: list[Finding], baseline: Baseline) -> list[Finding]:
    """Return *findings* with those present in *baseline* marked ``baselined``."""
    return [f.as_baselined() if f.fingerprint in baseline else f for f in findings]
