# SPDX-License-Identifier: Apache-2.0
"""Project-level analysis shared by command-line and editor integrations."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import codeguard.rules  # noqa: F401 -- register built-in rules
from codeguard.config import Config, ConfigError, find_config, load_config
from codeguard.engine.baseline import Baseline, apply_baseline
from codeguard.engine.discovery import DiscoveryConfig, discover, is_path_included
from codeguard.engine.finding import Finding
from codeguard.engine.policy import apply_config
from codeguard.engine.registry import REGISTRY
from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.registry import language_for_path


@dataclass(frozen=True)
class AnalysisOptions:
    """Options that affect both workspace and in-memory document analysis."""

    config_path: Path | None = None
    baseline_path: Path | None = None
    rule_ids: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()
    includes: tuple[str, ...] = ()
    no_gitignore: bool = False
    now: date | None = None


class ProjectAnalyzer:
    """Analyze a workspace while applying CodeGuard's normal project policy."""

    def __init__(self, workspace_root: Path, options: AnalysisOptions | None = None) -> None:
        self.workspace_root = workspace_root.resolve()
        self.options = options or AnalysisOptions()
        self.config = Config()
        self.root = self.workspace_root
        self.runner = AnalysisRunner()
        self.discovery = DiscoveryConfig()
        self.baseline: Baseline | None = None
        self._lock = threading.RLock()
        self.reload()

    def reload(self) -> None:
        """Reload configuration, active rules, discovery policy, and baseline."""
        config_file = self.options.config_path or find_config(self.workspace_root)
        config = load_config(config_file)
        root = Path(config.source_dir).resolve() if config.source_dir else self.workspace_root

        selected = list(self.options.rule_ids) or config.enable or None
        active_ids = active_rule_ids(config, selected)

        baseline_path = self.options.baseline_path
        if baseline_path is None and config.baseline:
            candidate = root / config.baseline
            if candidate.is_file():
                baseline_path = candidate

        baseline = None
        if baseline_path is not None:
            try:
                baseline = Baseline.load(baseline_path)
            except ValueError as exc:
                raise ConfigError(str(exc)) from exc

        with self._lock:
            self.config = config
            self.root = root
            self.runner = AnalysisRunner(
                rule_ids=active_ids, now=self.options.now, fingerprint_root=root
            )
            self.discovery = discovery_config(
                config,
                includes=self.options.includes,
                excludes=self.options.excludes,
                no_gitignore=self.options.no_gitignore,
            )
            self.baseline = baseline

    def files(self) -> list[Path]:
        """Discover supported workspace files using the configured policy."""
        with self._lock:
            return discover([self.workspace_root], self.discovery, root=self.root)

    def scan_workspace(self, *, jobs: int | None = None) -> list[Finding]:
        """Scan every discovered workspace file and apply project policy."""
        with self._lock:
            self.reload()
            n_jobs = self.config.jobs if jobs is None else jobs
            if n_jobs == 0:
                import os

                n_jobs = os.cpu_count() or 1
            findings = self.runner.run_files(self.files(), jobs=n_jobs)
            return self._apply_policy(findings)

    def scan_document(self, source: str, filename: str | Path) -> list[Finding]:
        """Scan an in-memory document using its on-disk path for project policy."""
        with self._lock:
            self.reload()
            path = Path(filename)
            language = language_for_path(path)
            if language is None or not is_path_included(path, self.discovery, root=self.root):
                return []
            findings = self.runner.run(source, filename=str(path), language=language)
            return self._apply_policy(findings)

    def scan_saved_file(self, filename: str | Path) -> list[Finding]:
        """Scan one saved file, returning no findings when it no longer exists."""
        with self._lock:
            self.reload()
            path = Path(filename)
            if not path.is_file() or not is_path_included(path, self.discovery, root=self.root):
                return []
            return self._apply_policy(self.runner.run_file(path))

    def _apply_policy(self, findings: list[Finding]) -> list[Finding]:
        return apply_project_policy(findings, self.config, root=self.root, baseline=self.baseline)


def active_rule_ids(config: Config, selected: list[str] | None = None) -> list[str]:
    """Resolve and validate the active rule IDs for a project."""
    if selected is not None:
        unknown = [rule_id for rule_id in selected if rule_id not in REGISTRY]
        if unknown:
            raise ConfigError(f"unknown rule ID(s): {', '.join(unknown)}")
    disabled = set(config.disable)
    return [
        rule.id
        for rule in REGISTRY.all()
        if (selected is None or rule.id in selected) and rule.id not in disabled
    ]


def discovery_config(
    config: Config,
    *,
    includes: tuple[str, ...] = (),
    excludes: tuple[str, ...] = (),
    no_gitignore: bool = False,
) -> DiscoveryConfig:
    """Build file-discovery policy shared by CLI and editor integrations."""
    return DiscoveryConfig(
        include=[*config.include, *includes],
        exclude=[*config.exclude, *excludes],
        respect_gitignore=config.gitignore and not no_gitignore,
    )


def apply_project_policy(
    findings: list[Finding],
    config: Config,
    *,
    root: Path,
    baseline: Baseline | None = None,
) -> list[Finding]:
    """Apply configuration and baseline policy, returning deterministically sorted results."""
    findings = apply_config(findings, config, root=str(root))
    if baseline is not None:
        findings = apply_baseline(findings, baseline)
    findings.sort(key=lambda item: (item.location.file, item.location.line, item.location.col))
    return findings
