# SPDX-License-Identifier: Apache-2.0
"""Baseline files -- freeze the findings that exist today so CI only fails on new ones.

A baseline (schema 2) is a JSON file with one record per finding: its rule, file,
line and the ``codeguard/v2`` identity keys (:mod:`codeguard.engine.identity`).
``scan --baseline path`` pairs the scan's findings with those records **one to one**,
file by file (renamed files included, see :mod:`codeguard.engine.filepairs`), through
the passes of :mod:`codeguard.engine.matcher`; a paired finding is marked
``baselined`` and excluded from the exit code, an unpaired one is new.  One record
hides one finding: a second copy of a baselined statement is reported.

Schema-1 files (a map of ``codeguard/v1`` fingerprints) still load: each entry becomes a
record with only the ``v1`` key, which the matcher's ``v1`` pass compares.  The next
``codeguard baseline update`` writes schema 2.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .filepairs import FilePair, PairConfig, pair_files
from .finding import Finding, MatchInfo
from .fingerprint import relative_path
from .identity import SCHEME, IdentityRecord
from .matcher import Match, MatchConfig, match

SCHEMA_VERSION = 2

#: Keys worth storing in a baseline (the tie-break keys included).
_STORED_KEYS = ("stmt", "nscope", "ident", "body", "lh", "ctx_prev", "ctx_next", "v1")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class BaselineRecord:
    """One baselined finding."""

    rule: str
    file: str
    line: int
    scope: str = ""
    keys: dict[str, str] = field(default_factory=dict)
    tokens: tuple[str, ...] = ()
    idents: tuple[str, ...] = ()
    header: bool = False
    first_seen: str = field(default_factory=_now)

    @classmethod
    def from_finding(cls, f: Finding, *, first_seen: str | None = None) -> BaselineRecord:
        rec = f.identity_record()
        return cls(
            rule=f.rule_id,
            file=f.location.file,
            line=f.location.line,
            scope=rec.scope,
            keys={k: v for k, v in rec.keys.items() if k in _STORED_KEYS and v},
            tokens=tuple(sorted(rec.tokens)),
            idents=tuple(sorted(rec.idents)),
            header=rec.header,
            first_seen=first_seen or _now(),
        )

    @property
    def v1(self) -> str:
        return self.keys.get("v1", "")

    def identity(self) -> IdentityRecord:
        return IdentityRecord(
            rule=self.rule,
            file=self.file,
            line=self.line,
            scope=self.scope,
            keys=dict(self.keys),
            tokens=frozenset(self.tokens),
            header=self.header,
            idents=frozenset(self.idents),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "rule": self.rule,
            "file": self.file,
            "line": self.line,
            "scope": self.scope,
            "keys": {k: self.keys[k] for k in sorted(self.keys)},
            "first_seen": self.first_seen,
        }
        if self.tokens:
            out["tokens"] = list(self.tokens)
        if self.idents:
            out["idents"] = list(self.idents)
        if self.header:
            out["header"] = True
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BaselineRecord:
        keys = data.get("keys", {})
        if not isinstance(keys, Mapping):
            raise ValueError("'keys' must be an object")
        return cls(
            rule=str(data["rule"]),
            file=str(data["file"]),
            line=int(data.get("line", 0)),
            scope=str(data.get("scope", "")),
            keys={str(k): str(v) for k, v in keys.items()},
            tokens=tuple(str(t) for t in data.get("tokens", ())),
            idents=tuple(str(t) for t in data.get("idents", ())),
            header=bool(data.get("header", False)),
            first_seen=str(data.get("first_seen", _now())),
        )


@dataclass(frozen=True)
class Pairing:
    """One baseline record paired with one finding (indices into the two lists)."""

    record: int
    finding: int
    match: Match
    files: FilePair


@dataclass
class Baseline:
    """The contents of a baseline file."""

    records: list[BaselineRecord] = field(default_factory=list)
    tool_version: str = "0.0.0"
    created: str = field(default_factory=_now)
    #: The commit the baseline was taken at, for rename detection; ``None`` if unknown.
    commit: str | None = None
    #: The schema version the file had when loaded (2 for a new baseline).
    schema_version: int = SCHEMA_VERSION

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_findings(
        cls,
        findings: Iterable[Finding],
        *,
        tool_version: str = "0.0.0",
        commit: str | None = None,
    ) -> Baseline:
        b = cls(tool_version=tool_version, commit=commit)
        b.records = [BaselineRecord.from_finding(f) for f in findings if _baselinable(f)]
        b._sort()
        return b

    @classmethod
    def load(cls, path: Path) -> Baseline:
        """Load a baseline file of schema 1 or 2.  Raises ``ValueError`` if malformed."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path}: cannot read baseline: {exc}") from exc
        if not isinstance(data, dict) or not ("fingerprints" in data or "findings" in data):
            raise ValueError(f"{path}: not a CodeGuard baseline file")
        try:
            return cls._from_dict(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{path}: malformed baseline: {exc}") from exc

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> Baseline:
        version = int(data.get("version", 1))
        out = cls(
            tool_version=str(data.get("tool_version", "0.0.0")),
            created=str(data.get("created", _now())),
            commit=str(data["commit"]) if data.get("commit") else None,
            schema_version=version,
        )
        if "findings" in data:
            items = data["findings"]
            if not isinstance(items, list):
                raise ValueError("'findings' must be a list")
            out.records = [BaselineRecord.from_dict(item) for item in items]
        else:
            fps = data["fingerprints"]
            if not isinstance(fps, dict):
                raise ValueError("'fingerprints' must be an object")
            for fp, meta in fps.items():
                meta = meta if isinstance(meta, dict) else {}
                out.records.append(
                    BaselineRecord(
                        rule=str(meta.get("rule_id", "")),
                        file=str(meta.get("file", "")),
                        line=0,
                        keys={"v1": str(fp)},
                        first_seen=str(meta.get("first_seen", out.created)),
                    )
                )
        out._sort()
        return out

    def _sort(self) -> None:
        self.records.sort(key=lambda r: (r.file, r.rule, r.line, r.v1))

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def __contains__(self, fingerprint: object) -> bool:
        """Whether a ``codeguard/v1`` fingerprint is in the baseline (compatibility)."""
        return any(r.v1 == fingerprint for r in self.records)

    def __len__(self) -> int:
        return len(self.records)

    @property
    def fingerprints(self) -> dict[str, dict[str, str]]:
        """The schema-1 view: ``{v1 fingerprint: {rule_id, file, first_seen}}``."""
        return {
            r.v1: {"rule_id": r.rule, "file": r.file, "first_seen": r.first_seen}
            for r in self.records
            if r.v1
        }

    def pair(
        self,
        findings: list[Finding],
        *,
        renames: Mapping[str, str] | None = None,
        root: str | Path | None = None,
        config: MatchConfig | None = None,
        pair_config: PairConfig | None = None,
    ) -> list[Pairing]:
        """Pair the baseline's records with *findings*, file by file, one to one.

        *renames* maps old to new paths (relative to *root*, forward slashes), as
        :func:`codeguard.engine.gitdiff.renames_since` reports them.  Paths of records
        and findings are compared relative to *root* when it is given.
        """
        norm = _normalizer(root)
        rec_by_file: dict[str, list[int]] = defaultdict(list)
        for i, rec in enumerate(self.records):
            rec_by_file[norm(rec.file)].append(i)
        fnd_by_file: dict[str, list[int]] = defaultdict(list)
        for j, f in enumerate(findings):
            fnd_by_file[norm(f.location.file)].append(j)
        old_ids = [self.records[i].identity() for i in range(len(self.records))]
        new_ids = [f.identity_record() for f in findings]
        pairs = pair_files(
            rec_by_file,
            fnd_by_file,
            renames=renames,
            old_keys={p: [old_ids[i].key("lh") for i in idx] for p, idx in rec_by_file.items()},
            new_keys={p: [new_ids[j].key("lh") for j in idx] for p, idx in fnd_by_file.items()},
            config=pair_config,
        )
        out: list[Pairing] = []
        for fp in pairs:
            ridx = rec_by_file[fp.old]
            fidx = fnd_by_file[fp.new]
            for m in match([old_ids[i] for i in ridx], [new_ids[j] for j in fidx], config):
                out.append(Pairing(ridx[m.old], fidx[m.new], m, fp))
        return out

    # ------------------------------------------------------------------
    # Mutate
    # ------------------------------------------------------------------

    def updated_with(
        self,
        findings: list[Finding],
        *,
        add_new: bool = True,
        renames: Mapping[str, str] | None = None,
        root: str | Path | None = None,
        commit: str | None = None,
        config: MatchConfig | None = None,
    ) -> Baseline:
        """A copy that follows the code: matched records are replaced by their current
        finding (``first_seen`` kept), unmatched findings are added when *add_new*,
        and unmatched records are kept."""
        return self.update(
            findings, add_new=add_new, renames=renames, root=root, commit=commit, config=config
        )[0]

    def update(
        self,
        findings: list[Finding],
        *,
        add_new: bool = True,
        renames: Mapping[str, str] | None = None,
        root: str | Path | None = None,
        commit: str | None = None,
        config: MatchConfig | None = None,
    ) -> tuple[Baseline, int, int]:
        """:meth:`updated_with`, also returning how many records followed their
        finding and how many findings were added."""
        pairings = self.pair(findings, renames=renames, root=root, config=config)
        records = [
            BaselineRecord(
                rule=r.rule,
                file=r.file,
                line=r.line,
                scope=r.scope,
                keys=dict(r.keys),
                tokens=r.tokens,
                idents=r.idents,
                header=r.header,
                first_seen=r.first_seen,
            )
            for r in self.records
        ]
        matched_findings: set[int] = set()
        for p in pairings:
            records[p.record] = BaselineRecord.from_finding(
                findings[p.finding], first_seen=self.records[p.record].first_seen
            )
            matched_findings.add(p.finding)
        added = 0
        if add_new:
            fresh = [
                BaselineRecord.from_finding(f)
                for j, f in enumerate(findings)
                if j not in matched_findings and _baselinable(f)
            ]
            records.extend(fresh)
            added = len(fresh)
        out = Baseline(
            records=records,
            tool_version=self.tool_version,
            created=self.created,
            commit=commit if commit is not None else self.commit,
        )
        out._sort()
        return out, len(pairings), added

    def pruned(
        self,
        live: Iterable[Finding] | set[str],
        *,
        renames: Mapping[str, str] | None = None,
        root: str | Path | None = None,
        config: MatchConfig | None = None,
    ) -> Baseline:
        """A copy without the records no current finding pairs with.

        *live* is the current findings; a set of ``codeguard/v1`` fingerprints is still
        accepted for compatibility.
        """
        if isinstance(live, set):
            keep = [r for r in self.records if r.v1 in live]
        else:
            findings = list(live)
            pairings = self.pair(findings, renames=renames, root=root, config=config)
            keep = [
                BaselineRecord.from_finding(
                    findings[p.finding], first_seen=self.records[p.record].first_seen
                )
                for p in pairings
            ]
        out = Baseline(
            records=keep,
            tool_version=self.tool_version,
            created=self.created,
            commit=self.commit,
        )
        out._sort()
        return out

    # ------------------------------------------------------------------
    # Serialise
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {
            "version": SCHEMA_VERSION,
            "scheme": SCHEME,
            "created": self.created,
            "tool_version": self.tool_version,
            "commit": self.commit,
            "findings": [r.to_dict() for r in self.records],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")


def _baselinable(f: Finding) -> bool:
    return bool(f.identity is not None or f.fingerprint)


def _normalizer(root: str | Path | None) -> Any:
    if root is None:
        return lambda p: str(p).replace("\\", "/")
    base = str(root)
    return lambda p: relative_path(str(p), root=base)


def apply_baseline(
    findings: list[Finding],
    baseline: Baseline,
    *,
    renames: Mapping[str, str] | None = None,
    root: str | Path | None = None,
    strict: bool = False,
    config: MatchConfig | None = None,
) -> list[Finding]:
    """Return *findings* with those paired with a baseline record marked ``baselined``.

    With *strict*, a pairing the matcher flagged as ambiguous (several candidates
    shared the key and the tie-break guessed) is reported as new instead.
    """
    by_finding = {
        p.finding: p for p in baseline.pair(findings, renames=renames, root=root, config=config)
    }
    out: list[Finding] = []
    for j, f in enumerate(findings):
        p = by_finding.get(j)
        if p is None:
            out.append(f.with_match(MatchInfo("new")))
        elif strict and p.match.ambiguous:
            out.append(f.with_match(MatchInfo("ambiguous", p.match.pass_name, p.match.score)))
        else:
            status = "ambiguous" if p.match.ambiguous else "known"
            out.append(f.as_baselined(MatchInfo(status, p.match.pass_name, p.match.score)))
    return out
