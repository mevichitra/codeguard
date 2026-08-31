# SPDX-License-Identifier: Apache-2.0
"""Auxiliary CLI commands: list-rules, explain, validate, init."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

import codeguard.rules  # noqa: F401  -- register built-in rules
from codeguard.cli.formatters import finding_help_uri
from codeguard.config import ConfigError, find_config, load_config
from codeguard.engine.registry import REGISTRY

_STARTER_TOML = """\
# CodeGuard configuration -- https://mevichitra.github.io/codeguard/configuration/
# (In pyproject.toml, use the [tool.codeguard] table instead of [codeguard].)

[codeguard]
exclude = ["**/*.min.js", "tests/fixtures/**"]
fail_on = "high"          # exit 1 only on findings at or above this severity
gitignore = true

[codeguard.rules]
disable = []
"""


def register(group: click.Group) -> None:
    group.add_command(_list_rules)
    group.add_command(_explain)
    group.add_command(_validate)
    group.add_command(_init)


@click.command("list-rules")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.option("--language", "language", default=None, help="Filter by language.")
@click.option("--category", "category", default=None, help="Filter by category.")
@click.option("--severity", "severity", default=None, help="Filter by severity.")
def _list_rules(fmt: str, language: str | None, category: str | None, severity: str | None) -> None:
    """List every registered rule."""
    rows: list[dict[str, object]] = []
    for rule in REGISTRY.all():
        langs = sorted(lang.value for lang in rule.languages)
        if language and language.lower() not in langs:
            continue
        if category and rule.category.value != category.lower():
            continue
        if severity and rule.severity.value != severity.lower():
            continue
        rows.append(
            {
                "id": rule.id,
                "title": rule.title,
                "severity": rule.severity.value,
                "category": rule.category.value,
                "languages": langs,
                "cwe": rule.cwe,
            }
        )

    if fmt == "json":
        click.echo(json.dumps(rows, indent=2))
        return

    if not rows:
        click.echo("No rules match.")
        return
    width = max(len(str(row["id"])) for row in rows)
    for row in rows:
        langs_str = ",".join(row["languages"])  # type: ignore[arg-type]
        click.echo(f"{row['id']:<{width}}  {row['severity']:<8}  {langs_str:<20}  {row['title']}")


@click.command("explain")
@click.argument("rule_id")
def _explain(rule_id: str) -> None:
    """Show the full description of a rule."""
    rule = REGISTRY.get(rule_id)
    if rule is None:
        click.echo(f"Unknown rule: {rule_id}", err=True)
        sys.exit(2)
    langs = ", ".join(sorted(lang.value for lang in rule.languages))
    click.echo(f"{rule.id}  --  {rule.title}\n")
    click.echo(f"Severity:  {rule.severity.value}")
    click.echo(f"Category:  {rule.category.value}")
    click.echo(f"Languages: {langs}")
    if rule.cwe:
        click.echo(f"CWE:       {rule.cwe}")
    if rule.owasp:
        click.echo(f"OWASP:     {rule.owasp}")
    click.echo(f"Docs:      {rule.help_uri or finding_help_uri(rule.id)}\n")
    click.echo(rule.description)


@click.command("validate")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Config file to validate (default: discovered).",
)
def _validate(config_path: Path | None) -> None:
    """Validate a codeguard.toml (or pyproject [tool.codeguard])."""
    path = config_path or find_config()
    if path is None:
        click.echo("No config file found. Nothing to validate.")
        return
    try:
        cfg = load_config(path)
    except ConfigError as exc:
        click.echo(f"Invalid: {exc}", err=True)
        sys.exit(3)

    unknown = [
        rid
        for rid in {*cfg.enable, *cfg.disable, *cfg.severity_remap, *cfg.rules}
        if rid not in REGISTRY
    ]
    if unknown:
        click.echo(f"Invalid: {path}: unknown rule ID(s): {', '.join(sorted(unknown))}", err=True)
        sys.exit(3)
    conflict = set(cfg.enable) & set(cfg.disable)
    if conflict:
        click.echo(
            f"Invalid: {path}: rule(s) both enabled and disabled: {', '.join(sorted(conflict))}",
            err=True,
        )
        sys.exit(3)

    click.echo(f"OK: {path}")


@click.command("init")
@click.option("--force", is_flag=True, help="Overwrite an existing codeguard.toml.")
def _init(force: bool) -> None:
    """Write a starter codeguard.toml in the current directory."""
    target = Path("codeguard.toml")
    if target.exists() and not force:
        click.echo("codeguard.toml already exists (use --force to overwrite).", err=True)
        sys.exit(2)
    target.write_text(_STARTER_TOML, encoding="utf-8")
    click.echo(f"Wrote {target}")
