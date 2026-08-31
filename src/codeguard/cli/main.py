# SPDX-License-Identifier: Apache-2.0
"""CodeGuard CLI — entry point for the ``codeguard`` command."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

# Load all built-in rules (import for side-effect)
import codeguard.rules  # noqa: F401
from codeguard import __version__
from codeguard.engine.finding import Severity
from codeguard.engine.runner import AnalysisRunner

console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
EXIT_OK = 0  # no active findings
EXIT_FINDINGS = 1  # one or more active findings
EXIT_ERROR = 2  # usage or IO error


# ---------------------------------------------------------------------------
# CLI definition
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(__version__, prog_name="codeguard")
def cli() -> None:
    """CodeGuard — static analysis for Python, focused on security."""


@cli.command("scan")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json", "json-legacy", "sarif"], case_sensitive=False),
    default="human",
    show_default=True,
    help="Output format. 'json-legacy' is the deprecated pre-2.0 bare array.",
)
@click.option(
    "--rule",
    "rule_ids",
    multiple=True,
    metavar="RULE_ID",
    help="Only run the specified rule(s). Repeatable: --rule CG-SEC-001 --rule CG-SEC-002",
)
@click.option(
    "--severity",
    "min_severity",
    type=click.Choice(["critical", "high", "medium", "low", "info"], case_sensitive=False),
    default=None,
    help="Only report findings at or above this severity.",
)
@click.option(
    "--show-suppressed",
    is_flag=True,
    default=False,
    help="Include suppressed findings in output.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write output to a file instead of stdout.",
)
@click.option(
    "--exclude",
    "exclude_patterns",
    multiple=True,
    metavar="GLOB",
    help="Exclude files or directories matching these glob patterns. Repeatable.",
)
def scan(
    path: Path,
    output_format: str,
    rule_ids: tuple[str, ...],
    min_severity: str | None,
    show_suppressed: bool,
    output: Path | None,
    exclude_patterns: tuple[str, ...],
) -> None:
    """Scan PATH (file or directory) and report findings.

    Exit codes:
      0  No active findings.
      1  One or more findings found.
      2  Error (file not found, parse error, etc.).

    Examples:

    \b
      codeguard scan myproject/
      codeguard scan auth.py --format json
      codeguard scan src/ --format sarif -o results.sarif
      codeguard scan . --rule CG-SEC-001 --severity high
    """
    if rule_ids:
        from codeguard.engine.registry import REGISTRY

        invalid_ids = [rid for rid in rule_ids if rid not in REGISTRY]
        if invalid_ids:
            console.print(
                f"[bold red]Error:[/bold red] Invalid rule ID(s) specified: "
                f"{', '.join(invalid_ids)}."
            )
            sys.exit(EXIT_ERROR)

    runner = AnalysisRunner(
        rule_ids=list(rule_ids) if rule_ids else None,
        exclude=list(exclude_patterns) if exclude_patterns else None,
    )

    try:
        findings = runner.run_path(path)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(EXIT_ERROR)

    # Apply severity filter
    if min_severity:
        threshold = Severity(min_severity)
        findings = [f for f in findings if f.severity >= threshold or f.suppressed]

    # Format output
    from codeguard.cli.formatters import (
        format_human,
        format_json,
        format_json_legacy,
        format_sarif,
    )

    fmt = output_format.lower()
    if fmt == "human":
        text = format_human(findings, show_suppressed=show_suppressed)
    elif fmt == "json":
        text = format_json(findings, show_suppressed=show_suppressed, tool_version=__version__)
    elif fmt == "json-legacy":
        console.print(
            "[yellow]warning:[/yellow] --format json-legacy is deprecated; "
            "switch to --format json (envelope object)."
        )
        text = format_json_legacy(findings, show_suppressed=show_suppressed)
    elif fmt == "sarif":
        text = format_sarif(findings, tool_version=__version__)
    else:
        console.print(f"[bold red]Unknown format:[/bold red] {output_format}")
        sys.exit(EXIT_ERROR)

    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"Results written to [bold]{output}[/bold]")
    else:
        click.echo(text, nl=False)

    # CI-friendly exit code
    active = [f for f in findings if not f.suppressed]
    sys.exit(EXIT_FINDINGS if active else EXIT_OK)
