# SPDX-License-Identifier: Apache-2.0
"""AST runner — executes registered rules against Python source files.

The runner is the only component that knows about both the registry and the
file system.  Rules know nothing about files; the runner knows nothing about
what rules detect.
"""

from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

from .finding import Finding
from .registry import REGISTRY, RuleRegistry

# Matches:  # codeguard: ignore[CG-SEC-001]
#           # codeguard: ignore[CG-SEC-001, CG-SEC-002]
_SUPPRESS_RE = re.compile(r"#\s*codeguard:\s*ignore\[([^\]]+)\]")

# Matches:  # codeguard: disable[CG-SEC-001]
#           # codeguard: disable[CG-SEC-001, CG-SEC-002]
_DISABLE_RE = re.compile(r"#\s*codeguard:\s*disable\[([^\]]+)\]")


def _parse_suppressions(source: str) -> dict[int, set[str]]:
    """Scan *source* for inline suppression comments and return a map.

    Returns
    -------
    dict[int, set[str]]
        ``{line_number: {rule_id, ...}}``, 1-indexed.  Lines without a
        suppression comment are absent from the dict.
    """
    suppressions: dict[int, set[str]] = {}
    for lineno, line in enumerate(source.splitlines(), start=1):
        match = _SUPPRESS_RE.search(line)
        if match:
            rule_ids = {rid.strip() for rid in match.group(1).split(",")}
            suppressions[lineno] = rule_ids
    return suppressions


def _parse_file_disables(source: str) -> set[str]:
    """Scan *source* for file-level disable comments and return a set of rule IDs."""
    disables: set[str] = set()
    for line in source.splitlines():
        match = _DISABLE_RE.search(line)
        if match:
            rule_ids = {rid.strip() for rid in match.group(1).split(",")}
            disables.update(rule_ids)
    return disables


class AnalysisRunner:
    """Runs registered rules against Python source code.

    Parameters
    ----------
    registry:
        Which rule registry to use.  Defaults to the module-level
        :data:`~codeguard.engine.registry.REGISTRY` singleton.
    rule_ids:
        When provided, only rules whose IDs are in this collection are run.
        Unknown IDs are silently ignored (the runner doesn't validate them).
    """

    def __init__(
        self,
        registry: RuleRegistry | None = None,
        rule_ids: list[str] | None = None,
    ) -> None:
        self._registry = registry if registry is not None else REGISTRY
        self._filter: set[str] | None = set(rule_ids) if rule_ids is not None else None

    @property
    def _active_rules(self) -> list:  # type: ignore[type-arg]
        if self._filter is None:
            return self._registry.all()
        return [r for r in self._registry.all() if r.id in self._filter]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, source: str, filename: str = "<stdin>") -> list[Finding]:
        """Analyse *source* text and return findings, suppressions applied.

        Findings are sorted by ``(location.line, rule_id)``.

        Suppressed findings are **included** with ``suppressed=True`` — callers
        that only want actionable findings should filter on ``f.suppressed``.

        Parameters
        ----------
        source:
            Raw Python source code.
        filename:
            Used in :class:`~codeguard.engine.finding.Location`.

        Raises
        ------
        SyntaxError
            If *source* is not valid Python.  Callers should handle this;
            see :meth:`run_file` for a version that handles it gracefully.
        """
        tree = ast.parse(source, filename=filename)
        suppressions = _parse_suppressions(source)
        file_disables = _parse_file_disables(source)
        findings: list[Finding] = []

        for rule in self._active_rules:
            for finding in rule.check(tree, source, filename):
                if finding.rule_id in file_disables or finding.rule_id in suppressions.get(
                    finding.location.line, set()
                ):
                    finding = finding.as_suppressed()
                findings.append(finding)

        findings.sort(key=lambda f: (f.location.line, f.rule_id))
        return findings

    def run_file(self, path: Path) -> list[Finding]:
        """Analyse a single ``.py`` file on disk.

        Returns an empty list and emits a :class:`SyntaxWarning` if the file
        cannot be parsed, rather than raising.
        """
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warnings.warn(f"Cannot read {path}: {exc}", stacklevel=2)
            return []

        try:
            return self.run(source, filename=str(path))
        except SyntaxError as exc:
            warnings.warn(
                f"Skipping {path}: syntax error on line {exc.lineno} — {exc.msg}",
                SyntaxWarning,
                stacklevel=2,
            )
            return []

    def run_path(self, path: Path) -> list[Finding]:
        """Analyse a file or directory (``*.py``, recursive).

        Parameters
        ----------
        path:
            A ``.py`` file, or a directory to scan recursively.

        Returns
        -------
        list[Finding]
            All findings from all files, sorted by ``(file, line, rule_id)``.
        """
        if path.is_file():
            return self.run_file(path)

        findings: list[Finding] = []
        for py_file in sorted(path.rglob("*.py")):
            findings.extend(self.run_file(py_file))

        findings.sort(key=lambda f: (f.location.file, f.location.line, f.rule_id))
        return findings
