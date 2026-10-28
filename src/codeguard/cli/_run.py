# SPDX-License-Identifier: Apache-2.0
"""Shared implementation behind ``codeguard scan`` and ``codeguard ci``."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import click
from rich.console import Console

from codeguard import __version__
from codeguard.analysis import (
    active_rule_ids,
    apply_project_policy,
    discovery_config,
    effective_categories,
    rule_options_from,
    validate_rule_options,
)
from codeguard.cli import formatters as fmt
from codeguard.config import ConfigError, find_config, load_config
from codeguard.engine.baseline import Baseline
from codeguard.engine.discovery import DiscoveryConfig, discover
from codeguard.engine.finding import Finding
from codeguard.engine.fixes import apply_fixes, unified_diff
from codeguard.engine.gitdiff import changed_files, default_base, is_git_repo
from codeguard.engine.policy import gating_findings
from codeguard.engine.registry import REGISTRY
from codeguard.engine.runner import AnalysisRunner

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
EXIT_INTERNAL = 4

SEVERITIES = ["critical", "high", "medium", "low", "info"]
FORMATS = ["human", "json", "json-legacy", "sarif", "github", "rdjson", "junit"]


def console(no_color: bool) -> Console:
    return Console(stderr=True, no_color=no_color)


@dataclass
class RunOptions:
    paths: tuple[Path, ...]
    config_path: Path | None = None
    output_format: str | None = None
    rule_ids: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()
    includes: tuple[str, ...] = ()
    fail_on: str | None = None
    exit_zero: bool = False
    min_severity: str | None = None
    show_suppressed: bool = False
    no_gitignore: bool = False
    jobs: int | None = None
    quiet: bool = False
    no_color: bool = False
    stdin_filename: str = "stdin.py"
    output: Path | None = None
    baseline_path: Path | None = None
    baseline_strict: bool = False  # report ambiguous baseline matches as new
    now: str | None = None  # pin the date for `until=` suppression expiry
    diff_ref: str | None = None
    diff_auto: bool = False  # `ci` -- pick a base branch if diff_ref not given
    sarif_out: Path | None = None  # `ci` -- also write SARIF here
    categories: tuple[str, ...] = ()  # only run rules in these categories
    fix: bool = False  # apply safe autofixes in place
    fix_dry_run: bool = False  # print the safe autofixes as a diff, change nothing


def execute(opt: RunOptions) -> int:
    """Run a scan and return the process exit code."""
    err = console(opt.no_color)

    first = Path(opt.paths[0]) if opt.paths and str(opt.paths[0]) != "-" else Path.cwd()
    scan_root = first if first.is_dir() else first.parent

    try:
        cfg_file = opt.config_path or find_config(scan_root)
        config = load_config(cfg_file)
        validate_rule_options(config)
    except ConfigError as exc:
        err.print(f"[bold red]Config error:[/bold red] {exc}")
        return EXIT_CONFIG

    root = Path(config.source_dir) if config.source_dir else scan_root

    output_format = (opt.output_format or config.output).lower()
    fail_on = opt.fail_on
    if opt.min_severity and not fail_on:
        err.print("[yellow]warning:[/yellow] --severity is deprecated; use --fail-on.")
        fail_on = opt.min_severity
    threshold = (fail_on or config.fail_on).lower()

    n_jobs = opt.jobs if opt.jobs is not None else config.jobs
    if n_jobs == 0:
        n_jobs = os.cpu_count() or 1

    selected = list(opt.rule_ids) or config.enable or None
    if selected is not None:
        bad = [r for r in selected if r not in REGISTRY]
        if bad:
            err.print(f"[bold red]Error:[/bold red] unknown rule ID(s): {', '.join(bad)}.")
            return EXIT_USAGE
    try:
        categories = effective_categories(config, opt.categories, selected=selected)
        active_ids = active_rule_ids(config, selected, categories=categories)
    except ConfigError as exc:
        err.print(f"[bold red]Error:[/bold red] {exc}")
        return EXIT_USAGE
    if (opt.fix or opt.fix_dry_run) and any(str(p) == "-" for p in opt.paths):
        err.print("[bold red]Error:[/bold red] --fix cannot be used with stdin ('-').")
        return EXIT_USAGE
    now = None
    if opt.now:
        from datetime import date

        try:
            now = date.fromisoformat(opt.now)
        except ValueError:
            err.print(f"[bold red]Error:[/bold red] --now must be YYYY-MM-DD, got {opt.now!r}")
            return EXIT_USAGE
    runner = AnalysisRunner(rule_ids=active_ids, now=now, rule_options=rule_options_from(config))

    disc = discovery_config(
        config,
        includes=opt.includes,
        excludes=opt.excludes,
        no_gitignore=opt.no_gitignore,
    )

    # --- collect --------------------------------------------------------
    diff_ref = opt.diff_ref
    if diff_ref is None and opt.diff_auto:
        if not is_git_repo(root):
            err.print("[bold red]Error:[/bold red] not a git repository; `ci` needs one.")
            return EXIT_USAGE
        diff_ref = default_base(root)
        if diff_ref is None:
            err.print("[yellow]warning:[/yellow] no base branch found; scanning all files.")

    try:
        findings = _collect(opt, runner, disc, n_jobs, root, diff_ref, err)
    except SystemExit as exc:  # _collect signalled a usage error
        return int(exc.code or EXIT_USAGE)
    except Exception as exc:
        err.print(f"[bold red]Internal error:[/bold red] {exc}")
        return EXIT_INTERNAL

    # --- baseline ------------------------------------------------------
    baseline_path = opt.baseline_path
    if baseline_path is None and config.baseline:
        candidate = root / config.baseline
        if candidate.is_file():
            baseline_path = candidate
    if baseline_path is not None:
        try:
            baseline = Baseline.load(baseline_path)
        except ValueError as exc:
            err.print(f"[bold red]Config error:[/bold red] {exc}")
            return EXIT_CONFIG
    else:
        baseline = None

    strict = True if opt.baseline_strict else None
    findings = apply_project_policy(
        findings, config, root=root, baseline=baseline, baseline_strict=strict
    )
    findings.sort(key=lambda f: (f.location.file, f.location.line, f.location.col, f.rule_id))

    # --- autofix --------------------------------------------------------
    if opt.fix_dry_run:
        diff, fixed, files, skipped = _fix_files(findings, write=False)
        click.echo(diff, nl=False)
        if not opt.quiet:
            err.print(_fix_summary("Would fix", fixed, files, skipped))
        if opt.exit_zero:
            return EXIT_OK
        return EXIT_FINDINGS if gating_findings(findings, threshold) else EXIT_OK
    if opt.fix:
        _diff, fixed, changed, skipped = _fix_files(findings, write=True)
        if changed:
            rescanned = apply_project_policy(
                runner.run_files(changed),
                config,
                root=root,
                baseline=baseline,
                baseline_strict=strict,
            )
            changed_set = {str(p) for p in changed}
            findings = [f for f in findings if f.location.file not in changed_set] + rescanned
            findings.sort(
                key=lambda f: (f.location.file, f.location.line, f.location.col, f.rule_id)
            )
        if not opt.quiet:
            err.print(_fix_summary("Fixed", fixed, changed, skipped))

    # --- render -------------------------------------------------------
    text = _render(output_format, findings, opt, err)

    if opt.sarif_out is not None:
        opt.sarif_out.write_text(
            fmt.format_sarif(findings, tool_version=__version__), encoding="utf-8"
        )
        if not opt.quiet:
            err.print(f"SARIF written to [bold]{opt.sarif_out}[/bold]")

    if opt.output:
        opt.output.write_text(text, encoding="utf-8")
        if not opt.quiet:
            err.print(f"Results written to [bold]{opt.output}[/bold]")
    else:
        click.echo(text, nl=False)

    # --- exit code --------------------------------------------------
    if opt.exit_zero:
        return EXIT_OK
    return EXIT_FINDINGS if gating_findings(findings, threshold) else EXIT_OK


def _collect(
    opt: RunOptions,
    runner: AnalysisRunner,
    disc: DiscoveryConfig,
    jobs: int,
    root: Path,
    diff_ref: str | None,
    err: Console,
) -> list[Finding]:
    targets = list(opt.paths) or [Path(".")]

    if any(str(p) == "-" for p in targets):
        source = sys.stdin.read()
        try:
            return runner.run(source, filename=opt.stdin_filename)
        except SyntaxError as exc:
            err.print(f"[yellow]warning:[/yellow] stdin: syntax error on line {exc.lineno}")
            return []

    for p in targets:
        if not p.exists():
            err.print(f"[bold red]Error:[/bold red] path does not exist: {p}")
            raise SystemExit(EXIT_USAGE)

    files = discover(targets, disc, root=root)

    if diff_ref is not None:
        changed = {p.resolve() for p in changed_files(diff_ref, root=root)}
        files = [f for f in files if f.resolve() in changed]

    return runner.run_files(files, jobs=jobs)


def _render(output_format: str, findings: list[Finding], opt: RunOptions, err: Console) -> str:
    ss = opt.show_suppressed
    if output_format == "human":
        return fmt.format_human(findings, show_suppressed=ss)
    if output_format == "json":
        return fmt.format_json(findings, show_suppressed=ss, tool_version=__version__)
    if output_format == "json-legacy":
        if not opt.quiet:
            err.print("[yellow]warning:[/yellow] --format json-legacy is deprecated.")
        return fmt.format_json_legacy(findings, show_suppressed=ss)
    if output_format == "sarif":
        return fmt.format_sarif(findings, tool_version=__version__)
    if output_format == "github":
        return fmt.format_github(findings, show_suppressed=ss)
    if output_format == "rdjson":
        return fmt.format_rdjson(findings, show_suppressed=ss, tool_version=__version__)
    if output_format == "junit":
        return fmt.format_junit(findings, show_suppressed=ss)
    raise click.BadParameter(f"unknown format: {output_format}")


def _fix_summary(verb: str, fixed: int, files: list[Path], skipped: int) -> str:
    noun = "file" if len(files) == 1 else "files"
    text = f"{verb} {fixed} finding(s) in {len(files)} {noun}"
    if skipped:
        text += f" ({skipped} skipped: overlapping edits)"
    return text + "."


def _fix_files(findings: list[Finding], *, write: bool) -> tuple[str, int, list[Path], int]:
    """Apply (or preview) every safe fix, file by file.

    Returns ``(unified diff, findings fixed, files changed, findings skipped)``.
    Files that are not valid UTF-8 are left alone.
    """
    by_file: dict[str, list[Finding]] = {}
    for f in findings:
        if f.fix is not None and f.fix.safe and not f.suppressed and not f.baselined:
            by_file.setdefault(f.location.file, []).append(f)

    diffs: list[str] = []
    fixed = skipped = 0
    changed: list[Path] = []
    for name in sorted(by_file):
        path = Path(name)
        try:
            raw = path.read_bytes()
            before = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        result = apply_fixes(before, by_file[name])
        skipped += len(result.skipped)
        if not result.changed:
            continue
        fixed += len(result.applied)
        changed.append(path)
        diffs.append(unified_diff(path.as_posix(), before, result.source))
        if write:
            path.write_bytes(result.source.encode("utf-8"))
    return "".join(diffs), fixed, changed, skipped
