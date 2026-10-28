"""Run an analyzer on one file version and attach every scheme's key to each finding.

A scanner either runs an analyzer, recording what it finds when given an
:class:`observations.ObservationWriter`, or replays a recording
(:meth:`Scanner.from_observations`) and runs no analyzer at all: the findings come from
the cache, only the scheme keys are computed. Both paths build the observations the
same way, so a rescore reproduces a live replay exactly.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import codeguard.rules  # noqa: F401  (registers the built-in rules)
from codeguard.engine.registry import REGISTRY
from codeguard.lang.base import Language
from codeguard.lang.registry import language_for_path

from .analyzers import Analyzer, RawFinding, make_analyzer
from .categories import split_by_category
from .matching import Observation, collisions
from .observations import ObservationReader, ObservationWriter
from .schemes import FileContext, keys_for

#: Paths that are vendored, generated or minified, and so not worth tracking.
_SKIP_PARTS = ("node_modules/", "vendor/", "/dist/", "/build/", "site-packages/")
_SKIP_SUFFIXES = (".min.js", ".d.ts", ".bundle.js")
MAX_BYTES = 512 * 1024

#: Which paths each analyzer reads, as :meth:`analyzers.Analyzer.supports` answers, for
#: replaying a recording without the analyzer.
SUPPORTS: dict[str, Callable[[str], bool]] = {
    "codeguard": lambda path: language_for_path(path) is not None,
    "bandit": lambda path: path.endswith(".py"),
    "semgrep": lambda path: language_for_path(path) is not None,
}


def rule_ids_for(categories: Iterable[str]) -> list[str]:
    wanted = set(categories)
    return [r.id for r in REGISTRY.all() if r.category.value in wanted]


def is_candidate(path: str | None) -> bool:
    if path is None or language_for_path(path) is None:
        return False
    padded = "/" + path
    return not any(p in padded for p in _SKIP_PARTS) and not path.endswith(_SKIP_SUFFIXES)


@dataclass
class ScanResult:
    observations: list[Observation]
    lines: list[str]
    collisions: dict[str, int]
    #: The analyzer's findings as it reported them.
    findings: list[RawFinding] = field(default_factory=list)


class _RecordedAnalyzer:
    """Stands in for the analyzer when a recording is replayed; never analyses."""

    def __init__(self, reader: ObservationReader) -> None:
        self.name = reader.analyzer
        self._supports = SUPPORTS[self.name]
        self._info = dict(reader.meta["analyzer"])
        self._source = str(reader.directory)

    def supports(self, path: str) -> bool:
        return self._supports(path)

    def analyze(self, path: str, text: str) -> list[RawFinding] | None:
        raise RuntimeError(f"{path}: not in the recording {self._source}")

    def describe(self) -> dict[str, Any]:
        return {**self._info, "observations": self._source}


class Scanner:
    """Scans file versions, caching by (blob, path) so a version is analysed once.

    *analyzer* is ``codeguard`` (runs *rule_ids*), ``bandit`` or ``semgrep`` (runs the
    rules in *semgrep_rules*, by default ``semgrep_rules.yml``); see :mod:`analyzers`.
    With *record_to*, every scanned version is written to that recording.
    """

    def __init__(
        self,
        rule_ids: list[str],
        schemes: Sequence[str],
        *,
        analyzer: str = "codeguard",
        semgrep_rules: Path | None = None,
        record_to: ObservationWriter | None = None,
        _reader: ObservationReader | None = None,
    ) -> None:
        self.analyzer: Analyzer = (
            _RecordedAnalyzer(_reader)
            if _reader is not None
            else make_analyzer(analyzer, rule_ids=rule_ids, semgrep_rules=semgrep_rules)
        )
        self._reader = _reader
        self._writer = record_to
        self._schemes = tuple(schemes)
        self._cache: dict[tuple[str, str], ScanResult | None] = {}
        self.versions_scanned = 0
        self.parse_failures = 0
        self.observations = 0
        self.collision_totals = dict.fromkeys(self._schemes, 0)
        #: The same counts split by rule category (see :mod:`categories`).
        self.category_observations: dict[str, int] = {}
        self.category_collisions: dict[str, dict[str, int]] = {}

    @classmethod
    def from_observations(cls, reader: ObservationReader, schemes: Sequence[str]) -> Scanner:
        """A scanner that takes its findings from *reader* and computes *schemes*' keys."""
        return cls([], schemes, _reader=reader)

    def scan(self, cache_key: str, path: str, data: bytes) -> ScanResult | None:
        """Findings for *path* with contents *data*; ``None`` if it cannot be analysed."""
        key = (cache_key, path)
        if key in self._cache:
            return self._cache[key]
        if self._reader is not None:
            result, status = self._replay(cache_key, path, data)
        else:
            result, status = self._scan(path, data)
        self._cache[key] = result
        if self._writer is not None:
            self._writer.version(cache_key, path, status, result.findings if result else ())
        if result is not None and status != "unsupported":
            self.versions_scanned += 1
            self.observations += len(result.observations)
            for scheme, n in result.collisions.items():
                self.collision_totals[scheme] += n
            self._count_categories(result.observations)
        return result

    def prefetch(self, versions: Iterable[tuple[str, str, bytes]]) -> None:
        """Let an analyzer that scans in batches (Semgrep) scan ``(cache key, path, data)``
        versions ahead of :meth:`scan`; a no-op for the others."""
        prefetch = getattr(self.analyzer, "prefetch", None)
        if prefetch is None:
            return  # *versions* is never read, so a generator is never run
        texts = []
        for cache_key, path, data in versions:
            if (cache_key, path) in self._cache or len(data) > MAX_BYTES:
                continue
            if language_for_path(path) is not None and self.analyzer.supports(path):
                texts.append((path, data.decode("utf-8", errors="replace")))
        prefetch(texts)

    def describe(self) -> dict[str, Any]:
        """The analyzer's name, version and configuration."""
        return self.analyzer.describe()

    def _count_categories(self, observations: Sequence[Observation]) -> None:
        for category, obs in split_by_category(observations).items():
            seen = self.category_observations
            seen[category] = seen.get(category, 0) + len(obs)
            zeros = dict.fromkeys(self._schemes, 0)
            totals = self.category_collisions.setdefault(category, zeros)
            for scheme, n in collisions(obs, self._schemes).items():
                totals[scheme] += n

    def _scan(self, path: str, data: bytes) -> tuple[ScanResult | None, str]:
        lang = language_for_path(path)
        if lang is None or len(data) > MAX_BYTES:
            return None, "skipped"
        text = data.decode("utf-8", errors="replace")
        if not self.analyzer.supports(path):
            # Not a failure: the analyzer has nothing to say about this kind of file.
            return self._result(path, text, [], supported=False), "unsupported"
        findings = self.analyzer.analyze(path, text)
        if findings is None:
            self.parse_failures += 1
            return None, "parse"
        return self._result(path, text, findings, supported=True), "ok"

    def _replay(self, cache_key: str, path: str, data: bytes) -> tuple[ScanResult | None, str]:
        assert self._reader is not None
        rec = self._reader.version(cache_key, path)
        if rec.status == "skipped":
            return None, rec.status
        if rec.status == "parse":
            self.parse_failures += 1
            return None, rec.status
        text = data.decode("utf-8", errors="replace")
        supported = rec.status == "ok"
        return self._result(path, text, list(rec.findings), supported=supported), rec.status

    def _result(
        self, path: str, text: str, findings: list[RawFinding], *, supported: bool
    ) -> ScanResult:
        is_python = supported and language_for_path(path) is Language.PYTHON
        ctx = FileContext.build(path, text, is_python=is_python)
        observations = [
            Observation(
                rule=f.rule,
                line=f.line,
                col=f.col,
                keys=keys_for(f.rule, f.line, ctx, self._schemes, meta=f.meta),
                message=f.meta.message,
                lines=ctx.lines,
            )
            for f in findings
        ]
        return ScanResult(
            observations, ctx.lines, collisions(observations, self._schemes), findings
        )
