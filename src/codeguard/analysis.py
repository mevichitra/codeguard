# SPDX-License-Identifier: Apache-2.0
"""Project-level analysis shared by command-line and editor integrations."""

from __future__ import annotations

import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import codeguard.rules  # noqa: F401 -- register built-in rules
from codeguard.config import Config, ConfigError, find_config, load_config
from codeguard.engine.baseline import Baseline, apply_baseline
from codeguard.engine.discovery import DiscoveryConfig, discover, is_path_included
from codeguard.engine.finding import Finding
from codeguard.engine.gitdiff import renames_since
from codeguard.engine.policy import apply_config
from codeguard.engine.registry import REGISTRY
from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.base import Language
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
    #: Only run rules in these categories (empty = config, then *default_categories*).
    categories: tuple[str, ...] = ()
    #: Categories used when neither *categories* nor the config chooses.
    default_categories: tuple[str, ...] = ("security",)
    #: Per-category switches applied last (editor settings): ``{"quality": False}``.
    category_overrides: tuple[tuple[str, bool], ...] = ()
    #: Extra rules to disable on top of the config (e.g. from editor settings).
    disabled_rule_ids: tuple[str, ...] = ()
    #: Re-read config and baseline on every scan.  Long-lived callers such as the
    #: language server set this to ``False`` and call :meth:`ProjectAnalyzer.reload`
    #: when a config file changes.
    auto_reload: bool = True


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
        validate_rule_options(config)
        active_ids = active_rule_ids(
            config,
            selected,
            categories=_apply_overrides(
                effective_categories(
                    config,
                    self.options.categories,
                    selected=selected,
                    default=self.options.default_categories,
                ),
                self.options.category_overrides,
            ),
            extra_disabled=self.options.disabled_rule_ids,
        )

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
                rule_ids=active_ids,
                now=self.options.now,
                fingerprint_root=root,
                rule_options=rule_options_from(config),
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
            self._maybe_reload()
            n_jobs = self.config.jobs if jobs is None else jobs
            if n_jobs == 0:
                import os

                n_jobs = os.cpu_count() or 1
            findings = self.runner.run_files(self.files(), jobs=n_jobs)
            return self._apply_policy(findings)

    def scan_document(self, source: str, filename: str | Path) -> list[Finding]:
        """Scan an in-memory document using its on-disk path for project policy."""
        with self._lock:
            self._maybe_reload()
            path = Path(filename)
            language = language_for_path(path)
            if language is None or not is_path_included(path, self.discovery, root=self.root):
                return []
            findings = self.runner.run(source, filename=str(path), language=language)
            return self._apply_policy(findings)

    def scan_saved_file(self, filename: str | Path) -> list[Finding]:
        """Scan one saved file, returning no findings when it no longer exists."""
        with self._lock:
            self._maybe_reload()
            path = Path(filename)
            if not path.is_file() or not is_path_included(path, self.discovery, root=self.root):
                return []
            return self._apply_policy(self.runner.run_file(path))

    def _maybe_reload(self) -> None:
        if self.options.auto_reload:
            self.reload()

    def _apply_policy(self, findings: list[Finding]) -> list[Finding]:
        return apply_project_policy(findings, self.config, root=self.root, baseline=self.baseline)


CATEGORIES = ("security", "performance", "quality", "ai-smell", "meta")

#: Categories ``scan`` / ``ci`` run when neither the command line nor the config
#: chooses: security only, so upgrading never changes a pipeline's exit code.
CLI_DEFAULT_CATEGORIES: tuple[str, ...] = ("security",)

#: Categories editors show by default: everything (diagnostics coach, not gate).
EDITOR_DEFAULT_CATEGORIES: tuple[str, ...] = ("security", "performance", "quality")


def effective_categories(
    config: Config,
    requested: Iterable[str] = (),
    *,
    selected: list[str] | None = None,
    default: tuple[str, ...] = CLI_DEFAULT_CATEGORIES,
) -> tuple[str, ...]:
    """Which categories to run.

    Precedence: *requested* (command line / editor setting), then the config's
    ``categories``, then *default*.  When rules are selected explicitly (``--rule``
    or ``[rules] enable``) and no category was requested, every category is
    allowed so the selection is honoured as written.
    """
    chosen = tuple(requested)
    if chosen:
        return chosen
    if selected:
        return ()
    if config.categories is not None:
        return tuple(config.categories)
    return default


def active_rule_ids(
    config: Config,
    selected: list[str] | None = None,
    *,
    categories: Iterable[str] = (),
    extra_disabled: Iterable[str] = (),
) -> list[str]:
    """Resolve and validate the active rule IDs for a project.

    *categories* (if non-empty) keeps only rules in those categories; meta rules
    are always kept so suppression hygiene still reports.  *extra_disabled*
    adds to ``config.disable``.
    """
    if selected is not None:
        unknown = [rule_id for rule_id in selected if rule_id not in REGISTRY]
        if unknown:
            raise ConfigError(f"unknown rule ID(s): {', '.join(unknown)}")
    wanted = {c.lower() for c in categories}
    bad = wanted - set(CATEGORIES)
    if bad:
        raise ConfigError(f"unknown categor(y/ies): {', '.join(sorted(bad))}")
    disabled = {*config.disable, *extra_disabled}
    return [
        rule.id
        for rule in REGISTRY.all()
        if (selected is None or rule.id in selected)
        and rule.id not in disabled
        and (not wanted or rule.category.value in wanted or rule.category.value == "meta")
    ]


def _apply_overrides(
    categories: tuple[str, ...], overrides: tuple[tuple[str, bool], ...]
) -> tuple[str, ...]:
    if not overrides:
        return categories
    if not categories:  # explicit rule selection: every category allowed
        return categories
    chosen = list(categories)
    for name, enabled in overrides:
        if enabled and name not in chosen:
            chosen.append(name)
        elif not enabled and name in chosen:
            chosen.remove(name)
    return tuple(chosen) or ("meta",)


def rule_options_from(config: Config) -> dict[str, dict[str, Any]]:
    """The ``[rules.<ID>]`` option overrides of *config*, keyed by rule ID."""
    return {rid: dict(rs.options) for rid, rs in config.rules.items() if rs.options}


def validate_rule_options(config: Config) -> None:
    """Check every ``[rules.<ID>]`` option against the rule's ``default_options``.

    Raises
    ------
    ConfigError
        For an option the rule does not declare, or a value of the wrong type.
    """
    for rule_id, settings in config.rules.items():
        if not settings.options:
            continue
        rule = REGISTRY.get(rule_id)
        if rule is None:
            continue  # unknown IDs are reported elsewhere
        known = dict(rule.default_options)
        for name, value in settings.options.items():
            if name not in known:
                allowed = ", ".join(["severity", "confidence_min", *sorted(known)])
                raise ConfigError(f"unknown option rules.{rule_id}.{name} (allowed: {allowed})")
            default = known[name]
            expected = type(default)
            ok = isinstance(value, expected) and not (
                isinstance(value, bool) and expected is not bool
            )
            if expected is float and isinstance(value, int) and not isinstance(value, bool):
                ok = True
            if not ok:
                raise ConfigError(
                    f"rules.{rule_id}.{name} must be {expected.__name__}, got {value!r}"
                )


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
        languages=frozenset(Language(name) for name in config.languages) or None,
    )


def apply_project_policy(
    findings: list[Finding],
    config: Config,
    *,
    root: Path,
    baseline: Baseline | None = None,
    baseline_strict: bool | None = None,
) -> list[Finding]:
    """Apply configuration and baseline policy, returning deterministically sorted results.

    The baseline is matched one to one, following renames git reports since the
    commit the baseline records (when *root* is a git repository).  *baseline_strict*
    (default: the config's ``baseline_strict``) reports ambiguous matches as new.
    """
    findings = apply_config(findings, config, root=str(root))
    if baseline is not None:
        renames = None
        if baseline.commit:
            renames = renames_since(baseline.commit, root=root)
        strict = config.baseline_strict if baseline_strict is None else baseline_strict
        findings = apply_baseline(findings, baseline, renames=renames, root=root, strict=strict)
    findings.sort(key=lambda item: (item.location.file, item.location.line, item.location.col))
    return findings
