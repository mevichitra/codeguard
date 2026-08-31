# SPDX-License-Identifier: Apache-2.0
"""CodeGuard CLI -- entry point for the ``codeguard`` command."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

# Load all built-in rules (import for side-effect)
import codeguard.rules  # noqa: F401
from codeguard import __version__
from codeguard.config import ConfigError, find_config, load_config
from codeguard.engine.discovery import DiscoveryConfig, discover
from codeguard.engine.finding import Finding
from codeguard.engine.policy import apply_config, gating_findings
from codeguard.engine.runner import AnalysisRunner

# ---------------------------------------------------------------------------
# Exit codes (stable contract -- see docs/exit-codes.md)
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
EXIT_INTERNAL = 4

# Back-compat alias (was EXIT_ERROR for both usage and IO errors).
EXIT_ERROR = EXIT_USAGE

_SEVERITIES = ["critical", "high", "medium", "low", "info"]


def _console(no_color: bool) -> Console:
    return Console(stderr=True, no_color=no_color)


@click.group()
@click.version_option(__version__, prog_name="codeguard")
def cli() -> None:
    """CodeGuard -- fast, offline static analysis for security anti-patterns."""


@cli.command("scan")
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to codeguard.toml (default: discovered from the working directory).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json", "json-legacy", "sarif"], case_sensitive=False),
    default=None,
    help="Output format [default: human, or config].",
)
@click.option(
    "--rule",
    "rule_ids",
    multiple=True,
    metavar="RULE_ID",
    help="Only run the specified rule(s). Repeatable.",
)
@click.option(
    "--exclude",
    "excludes",
    multiple=True,
    metavar="GLOB",
    help="Skip files matching this gitignore-style glob. Repeatable.",
)
@click.option(
    "--include",
    "includes",
    multiple=True,
    metavar="GLOB",
    help="Only scan files matching this glob. Repeatable.",
)
@click.option(
    "--fail-on",
    "fail_on",
    type=click.Choice([*_SEVERITIES, "never"], case_sensitive=False),
    default=None,
    help="Minimum severity that makes the run exit 1 [default: info, or config].",
)
@click.option("--exit-zero", is_flag=True, help="Always exit 0 (report-only).")
@click.option(
    "--severity",
    "min_severity",
    type=click.Choice(_SEVERITIES, case_sensitive=False),
    default=None,
    help="Deprecated alias of --fail-on.",
)
@click.option("--show-suppressed", is_flag=True, help="Include suppressed findings in output.")
@click.option("--no-gitignore", is_flag=True, help="Do not read .gitignore during discovery.")
@click.option(
    "--jobs",
    "-j",
    type=int,
    default=None,
    metavar="N",
    help="Parallel worker processes (0 = auto) [default: 1].",
)
@click.option("--quiet", "-q", is_flag=True, help="Only print findings, nothing else.")
@click.option("--no-color", is_flag=True, help="Disable coloured output.")
@click.option(
    "--stdin-filename",
    type=str,
    default="stdin.py",
    help="Filename to assume when reading from stdin ('-').",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write output to a file instead of stdout.",
)
def scan(
    paths: tuple[Path, ...],
    config_path: Path | None,
    output_format: str | None,
    rule_ids: tuple[str, ...],
    excludes: tuple[str, ...],
    includes: tuple[str, ...],
    fail_on: str | None,
    exit_zero: bool,
    min_severity: str | None,
    show_suppressed: bool,
    no_gitignore: bool,
    jobs: int | None,
    quiet: bool,
    no_color: bool,
    stdin_filename: str,
    output: Path | None,
) -> None:
    """Scan PATHS (files or directories; default '.') and report findings.

    Read from stdin with '-'.  Exit codes: 0 clean, 1 findings, 2 usage,
    3 config, 4 internal.
    """
    console = _console(no_color)

    # The project root anchors config discovery, .gitignore lookup, and the
    # relative paths used for globs and fingerprints.
    first = Path(paths[0]) if paths and str(paths[0]) != "-" else Path.cwd()
    scan_root = first if first.is_dir() else first.parent

    # --- config -----------------------------------------------------------
    try:
        cfg_file = config_path or find_config(scan_root)
        config = load_config(cfg_file)
    except ConfigError as exc:
        console.print(f"[bold red]Config error:[/bold red] {exc}")
        sys.exit(EXIT_CONFIG)

    root = Path(config.source_dir) if config.source_dir else scan_root

    fmt = (output_format or config.output).lower()
    if min_severity and not fail_on:
        console.print("[yellow]warning:[/yellow] --severity is deprecated; use --fail-on.")
        fail_on = min_severity
    threshold = (fail_on or config.fail_on).lower()
    n_jobs = jobs if jobs is not None else config.jobs
    if n_jobs == 0:
        import os

        n_jobs = os.cpu_count() or 1

    # --- rule filter -----------------------------------------------------
    from codeguard.engine.registry import REGISTRY

    selected = list(rule_ids) or config.enable or None
    disabled = set(config.disable)
    if selected is not None:
        bad = [r for r in selected if r not in REGISTRY]
        if bad:
            console.print(f"[bold red]Error:[/bold red] unknown rule ID(s): {', '.join(bad)}.")
            sys.exit(EXIT_USAGE)
    active_ids = [
        r.id
        for r in REGISTRY.all()
        if (selected is None or r.id in selected) and r.id not in disabled
    ]

    runner = AnalysisRunner(rule_ids=active_ids)

    # --- discovery + scan ----------------------------------------------
    disc = DiscoveryConfig(
        include=[*config.include, *includes],
        exclude=[*config.exclude, *excludes],
        respect_gitignore=config.gitignore and not no_gitignore,
    )

    try:
        findings = _collect(paths, runner, disc, n_jobs, stdin_filename, console, root)
    except Exception as exc:
        console.print(f"[bold red]Internal error:[/bold red] {exc}")
        sys.exit(EXIT_INTERNAL)

    findings = apply_config(findings, config, root=str(root))

    # --- format --------------------------------------------------------
    from codeguard.cli.formatters import (
        format_human,
        format_json,
        format_json_legacy,
        format_sarif,
    )

    if fmt == "human":
        text = format_human(findings, show_suppressed=show_suppressed)
    elif fmt == "json":
        text = format_json(findings, show_suppressed=show_suppressed, tool_version=__version__)
    elif fmt == "json-legacy":
        if not quiet:
            console.print("[yellow]warning:[/yellow] --format json-legacy is deprecated.")
        text = format_json_legacy(findings, show_suppressed=show_suppressed)
    else:  # sarif
        text = format_sarif(findings, tool_version=__version__)

    if output:
        output.write_text(text, encoding="utf-8")
        if not quiet:
            console.print(f"Results written to [bold]{output}[/bold]")
    else:
        click.echo(text, nl=False)

    # --- exit code ---------------------------------------------------
    if exit_zero:
        sys.exit(EXIT_OK)
    gating = gating_findings(findings, threshold)
    sys.exit(EXIT_FINDINGS if gating else EXIT_OK)


def _collect(
    paths: tuple[Path, ...],
    runner: AnalysisRunner,
    disc: DiscoveryConfig,
    jobs: int,
    stdin_filename: str,
    console: Console,
    root: Path,
) -> list[Finding]:
    targets = list(paths) or [Path(".")]

    if any(str(p) == "-" for p in targets):
        source = sys.stdin.read()
        try:
            return runner.run(source, filename=stdin_filename)
        except SyntaxError as exc:
            console.print(f"[yellow]warning:[/yellow] stdin: syntax error on line {exc.lineno}")
            return []

    for p in targets:
        if not p.exists():
            console.print(f"[bold red]Error:[/bold red] path does not exist: {p}")
            sys.exit(EXIT_USAGE)

    return runner.run_files(discover(targets, disc, root=root), jobs=jobs)


# Register the auxiliary commands.
from codeguard.cli import commands as _commands  # noqa: E402

_commands.register(cli)
