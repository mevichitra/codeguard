"""Run an analyzer on one file version and attach every scheme's key to each finding."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import codeguard.rules  # noqa: F401  (registers the built-in rules)
from codeguard.engine.registry import REGISTRY
from codeguard.lang.base import Language
from codeguard.lang.registry import language_for_path

from .analyzers import Analyzer, make_analyzer
from .categories import split_by_category
from .matching import Observation, collisions
from .schemes import FileContext, keys_for

#: Paths that are vendored, generated or minified, and so not worth tracking.
_SKIP_PARTS = ("node_modules/", "vendor/", "/dist/", "/build/", "site-packages/")
_SKIP_SUFFIXES = (".min.js", ".d.ts", ".bundle.js")
MAX_BYTES = 512 * 1024


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


class Scanner:
    """Scans file versions, caching by (blob, path) so a version is analysed once.

    *analyzer* is ``codeguard`` (runs *rule_ids*), ``bandit`` or ``semgrep`` (runs the
    rules in *semgrep_rules*, by default ``semgrep_rules.yml``); see :mod:`analyzers`.
    """

    def __init__(
        self,
        rule_ids: list[str],
        schemes: Sequence[str],
        *,
        analyzer: str = "codeguard",
        semgrep_rules: Path | None = None,
    ) -> None:
        self.analyzer: Analyzer = make_analyzer(
            analyzer, rule_ids=rule_ids, semgrep_rules=semgrep_rules
        )
        self._schemes = tuple(schemes)
        self._cache: dict[tuple[str, str], ScanResult | None] = {}
        self.versions_scanned = 0
        self.parse_failures = 0
        self.observations = 0
        self.collision_totals = dict.fromkeys(self._schemes, 0)
        #: The same counts split by rule category (see :mod:`categories`).
        self.category_observations: dict[str, int] = {}
        self.category_collisions: dict[str, dict[str, int]] = {}

    def scan(self, cache_key: str, path: str, data: bytes) -> ScanResult | None:
        """Findings for *path* with contents *data*; ``None`` if it cannot be analysed."""
        key = (cache_key, path)
        if key in self._cache:
            return self._cache[key]
        result = self._scan(path, data)
        self._cache[key] = result
        if result is not None and self.analyzer.supports(path):
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

    def _scan(self, path: str, data: bytes) -> ScanResult | None:
        lang = language_for_path(path)
        if lang is None or len(data) > MAX_BYTES:
            return None
        text = data.decode("utf-8", errors="replace")
        is_python = lang is Language.PYTHON
        if not self.analyzer.supports(path):
            # Not a failure: the analyzer has nothing to say about this kind of file.
            ctx = FileContext.build(path, text, is_python=False)
            return ScanResult([], ctx.lines, collisions([], self._schemes))
        findings = self.analyzer.analyze(path, text)
        if findings is None:
            self.parse_failures += 1
            return None
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
        return ScanResult(observations, ctx.lines, collisions(observations, self._schemes))
