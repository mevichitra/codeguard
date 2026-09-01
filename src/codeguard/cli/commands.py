# SPDX-License-Identifier: Apache-2.0
"""Auxiliary CLI commands: list-rules, explain, validate, init."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click

import codeguard.rules  # noqa: F401  -- register built-in rules
from codeguard import __version__
from codeguard.cli.formatters import finding_help_uri
from codeguard.config import ConfigError, find_config, load_config
from codeguard.engine.finding import Finding
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
    group.add_command(_run_demo)
    group.add_command(_list_rules)
    group.add_command(_explain)
    group.add_command(_validate)
    group.add_command(_init)
    group.add_command(_baseline)
    group.add_command(_suppressions)


def _find_demo_script() -> Path | None:
    """Find the showcase runner from a source checkout or nested working directory."""
    package_root = Path(__file__).resolve().parents[3]
    roots = [Path.cwd(), *Path.cwd().parents, package_root]
    seen: set[Path] = set()
    for root in roots:
        candidate = (root / "demos" / "run_demo.sh").resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    return None


@click.command("run")
def _run_demo() -> None:
    """Open the interactive showcase menu."""
    script = _find_demo_script()
    if script is None:
        raise click.ClickException(
            "demo suite not found; run this command from a CodeGuard source checkout"
        )
    completed = subprocess.run(["bash", str(script)], check=False)
    if completed.returncode:
        raise click.exceptions.Exit(completed.returncode)


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


# ---------------------------------------------------------------------------
# baseline
# ---------------------------------------------------------------------------


def _scan_for_baseline(paths: tuple[Path, ...], config_path: Path | None) -> list[Finding]:
    """Full scan (all rules, config applied) used to build/refresh a baseline."""
    from codeguard.config import load_config
    from codeguard.engine.discovery import DiscoveryConfig, discover
    from codeguard.engine.policy import apply_config
    from codeguard.engine.runner import AnalysisRunner

    targets = [Path(p) for p in paths] or [Path(".")]
    first = targets[0]
    root = first if first.is_dir() else first.parent

    cfg_file = config_path or find_config(root)
    config = load_config(cfg_file)
    cfg_root = Path(config.source_dir) if config.source_dir else root

    disc = DiscoveryConfig(
        include=list(config.include),
        exclude=list(config.exclude),
        respect_gitignore=config.gitignore,
    )
    findings = AnalysisRunner().run_files(discover(targets, disc, root=cfg_root))
    findings = apply_config(findings, config, root=str(cfg_root))
    return [f for f in findings if not f.suppressed]


@click.group("baseline")
def _baseline() -> None:
    """Create and maintain a baseline file (findings that must not fail CI)."""


@_baseline.command("create")
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path(".codeguard-baseline.json"),
    show_default=True,
)
def _baseline_create(paths: tuple[Path, ...], config_path: Path | None, output: Path) -> None:
    """Snapshot every current finding into a new baseline file."""
    from codeguard.engine.baseline import Baseline

    findings = _scan_for_baseline(paths, config_path)
    Baseline.from_findings(findings, tool_version=__version__).save(output)
    click.echo(f"Wrote {output} ({len(findings)} finding(s) baselined)")


@_baseline.command("update")
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
)
@click.option(
    "--baseline",
    "-b",
    "baseline_file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path(".codeguard-baseline.json"),
    show_default=True,
)
def _baseline_update(
    paths: tuple[Path, ...], config_path: Path | None, baseline_file: Path
) -> None:
    """Add newly-appeared findings to the baseline (keeps existing entries)."""
    from codeguard.engine.baseline import Baseline

    if not baseline_file.exists():
        click.echo(f"No baseline at {baseline_file}; run `baseline create` first.", err=True)
        sys.exit(2)
    findings = _scan_for_baseline(paths, config_path)
    before = len(Baseline.load(baseline_file))
    updated = Baseline.load(baseline_file).updated_with(findings)
    updated.save(baseline_file)
    click.echo(f"Updated {baseline_file} (+{len(updated) - before} new entry/entries)")


@_baseline.command("prune")
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
)
@click.option(
    "--baseline",
    "-b",
    "baseline_file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path(".codeguard-baseline.json"),
    show_default=True,
)
def _baseline_prune(paths: tuple[Path, ...], config_path: Path | None, baseline_file: Path) -> None:
    """Drop baseline entries whose finding no longer occurs."""
    from codeguard.engine.baseline import Baseline

    if not baseline_file.exists():
        click.echo(f"No baseline at {baseline_file}.", err=True)
        sys.exit(2)
    live = {f.fingerprint for f in _scan_for_baseline(paths, config_path) if f.fingerprint}
    before = len(Baseline.load(baseline_file))
    pruned = Baseline.load(baseline_file).pruned(live)
    pruned.save(baseline_file)
    click.echo(f"Pruned {baseline_file} (-{before - len(pruned)} stale entry/entries)")


# ---------------------------------------------------------------------------
# suppressions
# ---------------------------------------------------------------------------


@click.group("suppressions")
def _suppressions() -> None:
    """Inspect `# codeguard: ignore[...]` comments across the codebase."""


@_suppressions.command("list")
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
)
@click.option("--expired", is_flag=True, help="Show only expired suppressions (exit 1 if any).")
@click.option("--unused", is_flag=True, help="Show only suppressions that suppress nothing.")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.option(
    "--now",
    "now_str",
    metavar="YYYY-MM-DD",
    default=None,
    help="Date used to evaluate `until=` (default: today).",
)
def _suppressions_list(
    paths: tuple[Path, ...],
    config_path: Path | None,
    expired: bool,
    unused: bool,
    fmt: str,
    now_str: str | None,
) -> None:
    """List every suppression comment with its status (active / expired / unused)."""
    import json as _json
    from datetime import date

    from codeguard.config import load_config
    from codeguard.engine.discovery import DiscoveryConfig, discover
    from codeguard.engine.runner import AnalysisRunner
    from codeguard.engine.suppressions import SuppressionSet
    from codeguard.lang.registry import language_for_path

    today = date.fromisoformat(now_str) if now_str else date.today()

    targets = [Path(p) for p in paths] or [Path(".")]
    first = targets[0]
    root = first if first.is_dir() else first.parent
    config = load_config(config_path or find_config(root))
    cfg_root = Path(config.source_dir) if config.source_dir else root
    disc = DiscoveryConfig(
        include=list(config.include),
        exclude=list(config.exclude),
        respect_gitignore=config.gitignore,
    )
    files = discover(targets, disc, root=cfg_root)
    runner = AnalysisRunner()

    rows: list[dict[str, object]] = []
    for path in files:
        if language_for_path(path) is None:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        suppset = SuppressionSet.parse(source)
        if not suppset.all():
            continue
        try:
            findings = runner.run(source, filename=str(path), now=today)
        except SyntaxError:
            findings = []
        suppressed_at = {(f.rule_id, f.location.line) for f in findings if f.suppressed}
        suppressed_rules = {f.rule_id for f in findings if f.suppressed}

        for supp in suppset.all():
            if supp.is_expired(today):
                status = "expired"
            elif supp.file_level:
                status = "active" if supp.rule_ids & suppressed_rules else "unused"
            else:
                status = (
                    "active"
                    if any((rid, supp.line) in suppressed_at for rid in supp.rule_ids)
                    else "unused"
                )
            rows.append(
                {
                    "file": str(path),
                    "line": supp.line,
                    "rules": sorted(supp.rule_ids),
                    "scope": "file" if supp.file_level else "line",
                    "reason": supp.reason,
                    "until": supp.until.isoformat() if supp.until else None,
                    "status": status,
                }
            )

    if expired:
        rows = [r for r in rows if r["status"] == "expired"]
    if unused:
        rows = [r for r in rows if r["status"] == "unused"]

    if fmt == "json":
        click.echo(_json.dumps(rows, indent=2))
    elif not rows:
        click.echo("No suppressions." if not (expired or unused) else "None.")
    else:
        for r in rows:
            rules = ",".join(r["rules"])  # type: ignore[arg-type]
            reason = r["reason"] or "(no reason)"
            click.echo(f"{r['file']}:{r['line']}  {r['status']:<8} {rules:<24} {reason}")

    if expired and rows:
        sys.exit(1)
