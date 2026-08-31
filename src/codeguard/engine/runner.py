# SPDX-License-Identifier: Apache-2.0
"""Analysis runner -- executes registered rules against source files.

The runner is the only component that knows about both the registry and the
file system.  Rules know nothing about files; the runner knows nothing about
what rules detect.
"""

from __future__ import annotations

import re
import warnings
from collections.abc import Sequence
from fnmatch import fnmatch
from pathlib import Path

from codeguard.lang.base import Language
from codeguard.lang.registry import language_for_path, support_for

from . import fingerprint as _fp
from .context import RuleContext
from .finding import Finding
from .registry import REGISTRY, RuleRegistry
from .rule import Rule

# Matches:  # codeguard: ignore[CG-SEC-001]
#           # codeguard: ignore[CG-SEC-001, CG-SEC-002]
_SUPPRESS_RE = re.compile(r"(?:#|//)\s*codeguard:\s*ignore\[([^\]]+)\]")

# Matches:  # codeguard: disable[CG-SEC-001]   (file-level; alias: ignore-file)
_DISABLE_RE = re.compile(r"(?:#|//)\s*codeguard:\s*(?:disable|ignore-file)\[([^\]]+)\]")


def _parse_suppressions(source: str) -> dict[int, set[str]]:
    """Map line number (1-indexed) -> set of rule IDs suppressed on that line."""
    suppressions: dict[int, set[str]] = {}
    for lineno, line in enumerate(source.splitlines(), start=1):
        match = _SUPPRESS_RE.search(line)
        if match:
            suppressions[lineno] = {rid.strip() for rid in match.group(1).split(",")}
    return suppressions


def _parse_file_disables(source: str) -> set[str]:
    """Return the set of rule IDs disabled file-wide."""
    disables: set[str] = set()
    for line in source.splitlines():
        match = _DISABLE_RE.search(line)
        if match:
            disables.update(rid.strip() for rid in match.group(1).split(","))
    return disables


class AnalysisRunner:
    """Runs registered rules against source code.

    Parameters
    ----------
    registry:
        Which rule registry to use.  Defaults to the module-level
        :data:`~codeguard.engine.registry.REGISTRY` singleton.
    rule_ids:
        When provided, only rules whose IDs are in this collection are run.
    """

    def __init__(
        self,
        registry: RuleRegistry | None = None,
        rule_ids: list[str] | None = None,
        exclude: Sequence[str] | None = None,
    ) -> None:
        self._registry = registry if registry is not None else REGISTRY
        self._filter: set[str] | None = set(rule_ids) if rule_ids is not None else None
        self._exclude_patterns = [p.strip() for p in exclude or () if p.strip()]

    @property
    def _active_rules(self) -> list[Rule]:
        if self._filter is None:
            return self._registry.all()
        return [r for r in self._registry.all() if r.id in self._filter]

    def _rules_for(self, language: Language) -> list[Rule]:
        return [r for r in self._active_rules if language in r.languages]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        source: str,
        filename: str = "<stdin>",
        *,
        language: Language | None = None,
    ) -> list[Finding]:
        """Analyse *source* text and return findings, suppressions applied.

        Findings are sorted by ``(location.line, rule_id)`` and carry a
        fingerprint.  Suppressed findings are **included** with
        ``suppressed=True``.

        Parameters
        ----------
        source:
            Raw source code.
        filename:
            Used in :class:`~codeguard.engine.finding.Location` and to detect
            the language when *language* is not given.
        language:
            Force a language instead of detecting from *filename*.  Defaults to
            Python for ``"<stdin>"``.

        Raises
        ------
        SyntaxError
            If *source* is not valid for its language.  :meth:`run_file` handles
            this gracefully.
        ValueError
            If the language cannot be determined.
        """
        lang = language or language_for_path(filename) or Language.PYTHON
        support = support_for(lang)

        parsed = support.parse(source, filename)
        if not parsed.ok or parsed.root is None:
            err = parsed.error
            raise SyntaxError(
                (err.message if err else "parse error"),
                (filename, err.line if err else None, err.col if err else None, None),
            )

        ctx = RuleContext(
            filename=filename,
            source=source,
            language=lang,
            lang=support,
            root=parsed.root,  # type: ignore[arg-type]
        )
        suppressions = _parse_suppressions(source)
        file_disables = _parse_file_disables(source)
        rel = _fp.relative_path(filename)
        py_tree = ctx.python_ast if lang is Language.PYTHON else None

        findings: list[Finding] = []
        for rule in self._rules_for(lang):
            for finding in rule.analyze(ctx):
                line = finding.location.line
                line_ids = suppressions.get(line, set())
                if finding.rule_id in file_disables or finding.rule_id in line_ids:
                    finding = finding.as_suppressed()
                scope = _fp.python_scope(py_tree, line) if py_tree is not None else ""
                finding = finding.with_fingerprint(
                    _fp.compute(finding.rule_id, rel, source, line, scope=scope)
                )
                findings.append(finding)

        findings.sort(key=lambda f: (f.location.line, f.location.col, f.rule_id))
        return findings

    def run_file(self, path: Path) -> list[Finding]:
        """Analyse a single file on disk.

        Returns an empty list (and warns) for an unsupported extension, an
        unreadable file, or a syntax error, rather than raising.
        """
        lang = language_for_path(path)
        if lang is None:
            return []

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warnings.warn(f"Cannot read {path}: {exc}", stacklevel=2)
            return []

        try:
            return self.run(source, filename=str(path), language=lang)
        except SyntaxError as exc:
            warnings.warn(
                f"Skipping {path}: syntax error on line {exc.lineno} -- {exc.msg}",
                SyntaxWarning,
                stacklevel=2,
            )
            return []

    def run_path(self, path: Path) -> list[Finding]:
        """Analyse a file, or a directory recursively.

        Directory scanning currently walks every file with a supported
        extension; ``.gitignore`` and exclude handling arrive in a later
        milestone.
        """
        if path.is_file():
            return self.run_file(path)

        findings: list[Finding] = []
        for child in sorted(path.rglob("*")):
            if child.is_file() and language_for_path(child) is not None:
                if self._is_excluded(path, child):
                    continue
                findings.extend(self.run_file(child))

        findings.sort(key=lambda f: (f.location.file, f.location.line, f.location.col, f.rule_id))
        return findings

    def _is_excluded(self, root: Path, file_path: Path) -> bool:
        """Return True when a file should be excluded by glob patterns."""
        if not self._exclude_patterns:
            return False

        relative_path = file_path.relative_to(root).as_posix()

        for pattern in self._exclude_patterns:
            normalized_pattern = pattern.replace("\\", "/")
            if fnmatch(relative_path, normalized_pattern):
                return True
            if fnmatch(file_path.name, normalized_pattern):
                return True
            # Directory shorthand (e.g. "tests") excludes any path under that dir.
            if (
                "/" not in normalized_pattern
                and normalized_pattern in file_path.relative_to(root).parts
            ):
                return True

        return False
