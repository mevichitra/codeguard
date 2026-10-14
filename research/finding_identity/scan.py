"""Run CodeGuard on one file version and attach every scheme's key to each finding."""

from __future__ import annotations

import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import codeguard.rules  # noqa: F401  (registers the built-in rules)
from codeguard.engine.registry import REGISTRY
from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.base import Language
from codeguard.lang.registry import language_for_path

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
    """Scans file versions, caching by (blob, path) so a version is analysed once."""

    def __init__(self, rule_ids: list[str], schemes: Sequence[str]) -> None:
        self._runner = AnalysisRunner(rule_ids=rule_ids)
        self._schemes = tuple(schemes)
        self._cache: dict[tuple[str, str], ScanResult | None] = {}
        self.versions_scanned = 0
        self.parse_failures = 0
        self.observations = 0
        self.collision_totals = dict.fromkeys(self._schemes, 0)

    def scan(self, cache_key: str, path: str, data: bytes) -> ScanResult | None:
        """Findings for *path* with contents *data*; ``None`` if it cannot be analysed."""
        key = (cache_key, path)
        if key in self._cache:
            return self._cache[key]
        result = self._scan(path, data)
        self._cache[key] = result
        if result is not None:
            self.versions_scanned += 1
            self.observations += len(result.observations)
            for scheme, n in result.collisions.items():
                self.collision_totals[scheme] += n
        return result

    def _scan(self, path: str, data: bytes) -> ScanResult | None:
        lang = language_for_path(path)
        if lang is None or len(data) > MAX_BYTES:
            return None
        text = data.decode("utf-8", errors="replace")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                findings = self._runner.run(text, filename=path, language=lang)
        except (SyntaxError, ValueError, RecursionError):
            self.parse_failures += 1
            return None
        ctx = FileContext.build(path, text, is_python=lang is Language.PYTHON)
        observations = [
            Observation(
                rule=f.rule_id,
                line=f.location.line,
                col=f.location.col,
                keys=keys_for(f.rule_id, f.location.line, ctx, self._schemes),
            )
            for f in findings
        ]
        return ScanResult(observations, ctx.lines, collisions(observations, self._schemes))
