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
from codeguard.analysis import active_rule_ids, apply_project_policy, discovery_config
from codeguard.cli import formatters as fmt
from codeguard.config import ConfigError, find_config, load_config
from codeguard.engine.baseline import Baseline
from codeguard.engine.discovery import DiscoveryConfig, discover
from codeguard.engine.finding import Finding
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
    now: str | None = None  # pin the date for `until=` suppression expiry
    diff_ref: str | None = None
    diff_auto: bool = False  # `ci` -- pick a base branch if diff_ref not given
    sarif_out: Path | None = None  # `ci` -- also write SARIF here


def execute(opt: RunOptions) -> int:
    """Run a scan and return the process exit code."""
    err = console(opt.no_color)

    first = Path(opt.paths[0]) if opt.paths and str(opt.paths[0]) != "-" else Path.cwd()
    scan_root = first if first.is_dir() else first.parent

    try:
        cfg_file = opt.config_path or find_config(scan_root)
        config = load_config(cfg_file)
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
    active_ids = active_rule_ids(config, selected)
    now = None
    if opt.now:
        from datetime import date

        try:
            now = date.fromisoformat(opt.now)
        except ValueError:
            err.print(f"[bold red]Error:[/bold red] --now must be YYYY-MM-DD, got {opt.now!r}")
            return EXIT_USAGE
    runner = AnalysisRunner(rule_ids=active_ids, now=now)

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

    findings = apply_project_policy(findings, config, root=root, baseline=baseline)
    findings.sort(key=lambda f: (f.location.file, f.location.line, f.location.col, f.rule_id))

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
