# SPDX-License-Identifier: Apache-2.0
"""CodeGuard CLI -- entry point for the ``codeguard`` command."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

# Load all built-in rules (import for side-effect)
import codeguard.rules  # noqa: F401
from codeguard import __version__
from codeguard.cli._run import (
    EXIT_CONFIG,
    EXIT_FINDINGS,
    EXIT_INTERNAL,
    EXIT_OK,
    EXIT_USAGE,
    FORMATS,
    SEVERITIES,
    RunOptions,
    execute,
)

# Back-compat alias (was EXIT_ERROR for both usage and IO errors).
EXIT_ERROR = EXIT_USAGE

__all__ = [
    "EXIT_CONFIG",
    "EXIT_ERROR",
    "EXIT_FINDINGS",
    "EXIT_INTERNAL",
    "EXIT_OK",
    "EXIT_USAGE",
    "cli",
]


@click.group()
@click.version_option(__version__, prog_name="codeguard")
def cli() -> None:
    """CodeGuard -- fast, offline static analysis for security anti-patterns."""


# ---------------------------------------------------------------------------
# Options shared by `scan` and `ci`
# ---------------------------------------------------------------------------


_CmdFn = Callable[..., None]


def _common_options(fn: _CmdFn) -> _CmdFn:
    opts: list[Callable[[Any], Any]] = [
        click.argument("paths", nargs=-1, type=click.Path(path_type=Path)),
        click.option(
            "--config",
            "config_path",
            type=click.Path(exists=True, dir_okay=False, path_type=Path),
            help="Path to codeguard.toml (default: discovered).",
        ),
        click.option(
            "--format",
            "output_format",
            type=click.Choice(FORMATS, case_sensitive=False),
            default=None,
            help="Output format.",
        ),
        click.option(
            "--rule",
            "rule_ids",
            multiple=True,
            metavar="RULE_ID",
            help="Only run the specified rule(s). Repeatable.",
        ),
        click.option(
            "--exclude",
            "excludes",
            multiple=True,
            metavar="GLOB",
            help="Skip files matching this glob. Repeatable.",
        ),
        click.option(
            "--include",
            "includes",
            multiple=True,
            metavar="GLOB",
            help="Only scan files matching this glob. Repeatable.",
        ),
        click.option(
            "--fail-on",
            "fail_on",
            type=click.Choice([*SEVERITIES, "never"], case_sensitive=False),
            default=None,
            help="Min severity that makes the run exit 1.",
        ),
        click.option("--exit-zero", is_flag=True, help="Always exit 0 (report-only)."),
        click.option(
            "--severity",
            "min_severity",
            type=click.Choice(SEVERITIES, case_sensitive=False),
            default=None,
            help="Deprecated alias of --fail-on.",
        ),
        click.option(
            "--baseline",
            "baseline_path",
            type=click.Path(dir_okay=False, path_type=Path),
            default=None,
            help="Baseline file; findings in it do not fail the run.",
        ),
        click.option(
            "--show-suppressed",
            is_flag=True,
            help="Include suppressed / baselined findings in output.",
        ),
        click.option("--no-gitignore", is_flag=True, help="Do not read .gitignore."),
        click.option(
            "--jobs",
            "-j",
            type=int,
            default=None,
            metavar="N",
            help="Parallel worker processes (0 = auto).",
        ),
        click.option("--quiet", "-q", is_flag=True, help="Only print findings."),
        click.option("--no-color", is_flag=True, help="Disable coloured output."),
        click.option(
            "--output",
            "-o",
            type=click.Path(dir_okay=False, writable=True, path_type=Path),
            default=None,
            help="Write output to a file instead of stdout.",
        ),
    ]
    for opt in reversed(opts):
        fn = opt(fn)
    return fn


@cli.command("scan")
@_common_options
@click.option(
    "--diff",
    "diff_ref",
    metavar="REF",
    default=None,
    help="Only scan files changed since REF (merge-base with HEAD).",
)
@click.option(
    "--stdin-filename", default="stdin.py", help="Filename to assume when reading from stdin ('-')."
)
def scan(**kw: object) -> None:
    """Scan PATHS (files or directories; default '.') and report findings.

    Read from stdin with '-'.  Exit codes: 0 clean, 1 findings, 2 usage,
    3 config, 4 internal.
    """
    sys.exit(execute(RunOptions(**kw)))  # type: ignore[arg-type]


@cli.command("ci")
@_common_options
@click.option(
    "--diff",
    "diff_ref",
    metavar="REF",
    default=None,
    help="Base ref to diff against (default: auto-detect the PR base branch).",
)
@click.option(
    "--sarif",
    "sarif_out",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Also write a SARIF report to this path (for code-scanning upload).",
)
def ci(**kw: object) -> None:
    """Diff-aware scan for pull requests.

    Scans only files changed since the base branch, applies the baseline, and
    defaults to GitHub Actions annotations. Same exit-code contract as `scan`.
    """
    kw.setdefault("output_format", None)
    opt = RunOptions(diff_auto=True, **kw)  # type: ignore[arg-type]
    if opt.output_format is None:
        opt.output_format = "github"
    if not opt.paths:
        opt.paths = (Path("."),)
    sys.exit(execute(opt))


# Register the auxiliary commands (list-rules, explain, validate, init, baseline).
from codeguard.cli import commands as _commands  # noqa: E402

_commands.register(cli)
