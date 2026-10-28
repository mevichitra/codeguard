"""Observation cache: what the analyzer found in every file version a replay scanned.

Scoring an identity scheme needs only the analyzer's findings and the file text. The
findings are the expensive part (CodeGuard scans a corpus in twenty minutes, Semgrep in
three hours); the text is one ``git cat-file`` away. So a replay run with
``--observations`` records, per repository:

- ``versions.jsonl.gz``: one record per scanned file version, keyed by blob SHA and
  path: the scan's status and the raw findings (rule, line, column and the analyzer
  fields some schemes compare: message, severity, confidence, CWE, test name and, for
  Semgrep, the emitted ``match_based_id``). No scheme key is stored; keys are
  recomputed from the text, so a new scheme needs no new scan.
- ``pairs.jsonl``: the commit pairs in order, each with the file changes the replay
  looked at (``git diff -M``, filtered to analysable paths), so a rescore runs no diff.
- ``meta.json``: the run's label, repository, head, categories and the analyzer's
  description.

``rescore`` (:mod:`rescore`) then replays the same history from the cache and the
repository's blobs, with any set of schemes, in the same code path as a live replay.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from .analyzers import RawFinding
from .gitrepo import Change, GitRepo
from .schemes import FindingMeta

FORMAT = 1
VERSIONS = "versions.jsonl.gz"
PAIRS = "pairs.jsonl"
META = "meta.json"

#: Scan statuses: ``ok`` (findings recorded), ``unsupported`` (the analyzer does not read
#: this kind of file; the scheme keys still see its lines), ``parse`` (the analyzer could
#: not read the file) and ``skipped`` (no language, or over the size limit).
STATUSES = ("ok", "unsupported", "parse", "skipped")

_META_FIELDS = ("message", "severity", "confidence", "cwe", "test")


def _finding_to_json(f: RawFinding) -> dict[str, Any]:
    out: dict[str, Any] = {"rule": f.rule, "line": f.line, "col": f.col}
    for name in _META_FIELDS:
        value = getattr(f.meta, name)
        if value:
            out[name] = value
    if f.meta.semgrep_id is not None:
        out["semgrep_id"] = f.meta.semgrep_id
    return out


def _finding_from_json(d: dict[str, Any]) -> RawFinding:
    meta = FindingMeta(
        **{name: str(d.get(name, "")) for name in _META_FIELDS},
        semgrep_id=d.get("semgrep_id"),
    )
    return RawFinding(str(d["rule"]), int(d["line"]), int(d["col"]), meta)


@dataclass(frozen=True)
class VersionRecord:
    sha: str
    path: str
    status: str
    findings: tuple[RawFinding, ...] = ()


class ObservationWriter:
    """Records the versions a :class:`scan.Scanner` scans and the pairs a replay walks."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self._versions: IO[str] = gzip.open(directory / VERSIONS, "wt", encoding="utf-8")
        self._pairs: IO[str] = (directory / PAIRS).open("w", encoding="utf-8")
        self._seen: set[tuple[str, str]] = set()
        self.versions = 0
        self.pairs = 0

    def version(self, sha: str, path: str, status: str, findings: Sequence[RawFinding]) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown scan status {status!r}")
        if (sha, path) in self._seen:
            return
        self._seen.add((sha, path))
        rec: dict[str, Any] = {"sha": sha, "path": path, "status": status}
        if status == "ok":
            rec["findings"] = [_finding_to_json(f) for f in findings]
        self._versions.write(json.dumps(rec) + "\n")
        self.versions += 1

    def pair(self, old: str, new: str, changes: Sequence[Change]) -> None:
        rec = {
            "old": old,
            "new": new,
            "changes": [[c.status, c.old_path, c.new_path, c.old_sha, c.new_sha] for c in changes],
        }
        self._pairs.write(json.dumps(rec) + "\n")
        self.pairs += 1

    def close(self, meta: dict[str, Any]) -> None:
        self._versions.close()
        self._pairs.close()
        body = {"format": FORMAT, **meta, "versions": self.versions, "pairs": self.pairs}
        (self.directory / META).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


class ObservationReader:
    """A recorded run, loaded into memory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.meta: dict[str, Any] = json.loads((directory / META).read_text(encoding="utf-8"))
        if self.meta.get("format") != FORMAT:
            raise ValueError(f"{directory / META}: unsupported format {self.meta.get('format')!r}")
        self._versions: dict[tuple[str, str], VersionRecord] = {}
        with gzip.open(directory / VERSIONS, "rt", encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                findings = tuple(_finding_from_json(f) for f in d.get("findings", ()))
                rec = VersionRecord(d["sha"], d["path"], d["status"], findings)
                self._versions[(rec.sha, rec.path)] = rec
        self._pairs: list[tuple[str, str]] = []
        self._changes: dict[tuple[str, str], list[Change]] = {}
        with (directory / PAIRS).open(encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                key = (d["old"], d["new"])
                self._pairs.append(key)
                self._changes[key] = [Change(*c) for c in d["changes"]]

    @property
    def analyzer(self) -> str:
        return str(self.meta["analyzer"]["analyzer"])

    @property
    def history(self) -> list[str]:
        """The commits the recorded pairs walk, oldest first."""
        if not self._pairs:
            return []
        return [self._pairs[0][0], *(new for _, new in self._pairs)]

    def version(self, sha: str, path: str) -> VersionRecord:
        try:
            return self._versions[(sha, path)]
        except KeyError:
            raise KeyError(f"{self.directory}: no recorded scan of {path} at blob {sha}") from None

    def changes(self, old: str, new: str) -> list[Change]:
        try:
            return self._changes[(old, new)]
        except KeyError:
            raise KeyError(
                f"{self.directory}: commit pair {old[:12]}..{new[:12]} not recorded"
            ) from None

    def __len__(self) -> int:
        return len(self._versions)


class RecordedRepo(GitRepo):
    """A repository whose history and changes come from a recording; blobs from git."""

    def __init__(self, reader: ObservationReader, path: Path) -> None:
        super().__init__(path)
        self._reader = reader

    def resolve(self, ref: str) -> str:
        return str(self._reader.meta["head"])

    def first_parent_history(self, ref: str, count: int) -> list[str]:
        history = self._reader.history
        return history[-count:] if count < len(history) else history

    def changes(self, old: str, new: str) -> list[Change]:
        return self._reader.changes(old, new)
