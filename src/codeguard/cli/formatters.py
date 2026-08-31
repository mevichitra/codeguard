# SPDX-License-Identifier: Apache-2.0
"""Output formatters: human-readable, JSON, and SARIF."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from codeguard.engine.finding import Finding
from codeguard.engine.fingerprint import SCHEME as _FP_SCHEME

_SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")

_HELP_URI_BASE = "https://mevichitra.github.io/codeguard/rules/"


def finding_help_uri(rule_id: str) -> str:
    return f"{_HELP_URI_BASE}{rule_id.lower()}/"


def _muted(f: Finding) -> bool:
    """A finding hidden from the default view: suppressed or baselined."""
    return f.suppressed or f.baselined


# ---------------------------------------------------------------------------
# Human-readable (default)
# ---------------------------------------------------------------------------

_SEVERITY_COLOR = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "blue",
    "info": "dim",
}


def format_human(findings: list[Finding], *, show_suppressed: bool = False) -> str:
    """Return a human-readable string representation of *findings*.

    Suppressed and baselined findings are omitted unless *show_suppressed* is True.
    """
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=True)

    active = [f for f in findings if not _muted(f)]
    muted = [f for f in findings if _muted(f)]
    n_suppressed = sum(1 for f in muted if f.suppressed)
    n_baselined = sum(1 for f in muted if f.baselined and not f.suppressed)

    if not active and not (show_suppressed and muted):
        console.print("[bold green]✓ No findings.[/bold green]")
        return buf.getvalue()

    if show_suppressed:
        active = list(findings)

    _file_cache: dict[str, list[str]] = {}

    for f in active:
        color = _SEVERITY_COLOR.get(f.severity.value, "white")
        loc = f"{f.location.file}:{f.location.line}:{f.location.col}"
        sev = f.severity.value.upper()
        tag = (
            " [dim](suppressed)[/dim]"
            if f.suppressed
            else (" [dim](baselined)[/dim]" if f.baselined else "")
        )
        console.print(f"[dim]{loc}[/dim]  [{color}][{f.rule_id}] {sev}[/{color}]  {f.title}{tag}")

        # Show the offending source line with a column marker.
        try:
            if f.location.file not in _file_cache:
                with open(f.location.file, encoding="utf-8", errors="replace") as fh:
                    _file_cache[f.location.file] = fh.readlines()
            lines = _file_cache[f.location.file]
            line_idx = f.location.line - 1
            if 0 <= line_idx < len(lines):
                source = lines[line_idx].rstrip()
                gutter = f"{f.location.line:>4}"
                console.print(f"  {gutter} | {source}", style="dim", markup=False)
                pointer = " " * (len(gutter) + 3 + (f.location.col - 1)) + "^"
                console.print(f"  {pointer}", style="dim", markup=False)
        except OSError:
            pass

        if f.fix_suggestion:
            console.print(f"  [dim]→ {f.fix_suggestion}[/dim]")

    notes = []
    if n_suppressed:
        notes.append(f"{n_suppressed} suppressed")
    if n_baselined:
        notes.append(f"{n_baselined} baselined")
    if notes:
        console.print(f"\n[dim]({', '.join(notes)}, hidden — use --show-suppressed)[/dim]")

    _print_summary(console, [f for f in active if not _muted(f)])
    return buf.getvalue()


def _print_summary(console: Any, findings: list[Finding]) -> None:
    counts = Counter(f.severity.value for f in findings)
    total = len(findings)
    parts = []
    for sev in _SEVERITY_ORDER:
        n = counts.get(sev, 0)
        if n:
            parts.append(f"[{_SEVERITY_COLOR[sev]}]{n} {sev}[/{_SEVERITY_COLOR[sev]}]")
    summary = ", ".join(parts) if parts else "0"
    console.print(f"\n[bold]{total} finding(s)[/bold]  ({summary})")


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

#: Bump when the envelope shape changes in a backward-incompatible way.
JSON_SCHEMA_VERSION = "1"


def format_json(
    findings: list[Finding],
    *,
    show_suppressed: bool = False,
    tool_version: str = "0.0.0",
) -> str:
    """Return findings as a JSON envelope object.

    Shape: ``{ schema_version, tool, rules, results, summary }``.  ``results`` is
    a list of finding dicts (see :meth:`Finding.to_dict`).  For the pre-2.0 bare
    array, use :func:`format_json_legacy`.
    """
    emitted = findings if show_suppressed else [f for f in findings if not _muted(f)]

    rules: dict[str, dict[str, Any]] = {}
    for f in emitted:
        rules.setdefault(
            f.rule_id,
            {
                "id": f.rule_id,
                "title": f.title,
                "severity": f.severity.value,
                "category": f.category.value,
                "cwe": f.cwe,
                "owasp": f.owasp,
                "help_uri": finding_help_uri(f.rule_id),
            },
        )

    counts = Counter(f.severity.value for f in emitted)
    envelope = {
        "schema_version": JSON_SCHEMA_VERSION,
        "tool": {"name": "CodeGuard", "version": tool_version},
        "rules": [rules[k] for k in sorted(rules)],
        "results": [f.to_dict() for f in emitted],
        "summary": {
            "findings": len(emitted),
            "by_severity": {s: counts[s] for s in _SEVERITY_ORDER if counts.get(s)},
            "suppressed": sum(1 for f in findings if f.suppressed),
        },
    }
    return json.dumps(envelope, indent=2)


def format_json_legacy(findings: list[Finding], *, show_suppressed: bool = False) -> str:
    """Return findings as a bare JSON array (the pre-2.0 ``--format json`` output).

    Deprecated: retained for one minor version.  Prefer :func:`format_json`.
    """
    emitted = findings if show_suppressed else [f for f in findings if not _muted(f)]
    return json.dumps([f.to_dict() for f in emitted], indent=2)


# ---------------------------------------------------------------------------
# SARIF 2.1.0
# ---------------------------------------------------------------------------

_SARIF_SEVERITY = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "none",
}

_SECURITY_SEVERITY = {
    "critical": "9.5",
    "high": "8.0",
    "medium": "5.0",
    "low": "3.0",
    "info": "0.0",
}


def _cwe_number(cwe: str) -> str | None:
    if cwe and cwe.upper().startswith("CWE-"):
        return cwe[4:]
    return None


def format_sarif(findings: list[Finding], *, tool_version: str = "0.0.0") -> str:
    """Return findings as a SARIF 2.1.0 JSON string.

    SARIF is the standard format for static analysis results understood by
    GitHub code scanning.  https://docs.oasis-open.org/sarif/sarif/v2.1.0/

    Suppressed findings are included as ``suppressions`` entries per the spec.
    Every result carries ``partialFingerprints`` so alerts stay stable across
    reformatting and line moves.
    """
    rule_map: dict[str, Finding] = {}
    for f in findings:
        rule_map.setdefault(f.rule_id, f)

    rules = []
    for rule_id, f in sorted(rule_map.items()):
        tags = [f.category.value]
        cwe_n = _cwe_number(f.cwe or "")
        if cwe_n:
            tags.append(f"external/cwe/cwe-{cwe_n}")
        rule: dict[str, Any] = {
            "id": rule_id,
            "name": f.title,
            "shortDescription": {"text": f.title},
            "fullDescription": {"text": f.description},
            "helpUri": finding_help_uri(rule_id),
            "defaultConfiguration": {"level": _SARIF_SEVERITY.get(f.severity.value, "warning")},
            "properties": {
                "tags": tags,
                "security-severity": _SECURITY_SEVERITY.get(f.severity.value, "0.0"),
            },
        }
        if f.cwe:
            rule["properties"]["cwe"] = f.cwe
        if f.owasp:
            rule["properties"]["owasp"] = f.owasp
        if f.fix_suggestion:
            rule["help"] = {"text": f.fix_suggestion}
        rules.append(rule)

    results = []
    for f in findings:
        region: dict[str, Any] = {
            "startLine": f.location.line,
            "startColumn": f.location.col,
        }
        if f.location.end_line is not None:
            region["endLine"] = f.location.end_line
        if f.location.end_col is not None:
            region["endColumn"] = f.location.end_col

        result: dict[str, Any] = {
            "ruleId": f.rule_id,
            "level": _SARIF_SEVERITY.get(f.severity.value, "warning"),
            "message": {"text": f.description},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.location.file, "uriBaseId": "%SRCROOT%"},
                        "region": region,
                    }
                }
            ],
            "properties": {
                "confidence": f.confidence,
                "severity": f.severity.value,
            },
        }
        if f.fingerprint:
            result["partialFingerprints"] = {_FP_SCHEME: f.fingerprint}
        if f.suppressed:
            result["suppressions"] = [{"kind": "inSource", "justification": "inline ignore"}]
        elif f.baselined:
            result["suppressions"] = [{"kind": "external", "justification": "in baseline"}]
        results.append(result)

    sarif: dict[str, Any] = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "CodeGuard",
                        "version": tool_version,
                        "informationUri": "https://github.com/mevichitra/codeguard",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2)


# ---------------------------------------------------------------------------
# GitHub Actions workflow-command annotations
# ---------------------------------------------------------------------------

_GH_LEVEL = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "notice",
    "info": "notice",
}


def _reportable(findings: list[Finding], *, show_suppressed: bool) -> list[Finding]:
    if show_suppressed:
        return list(findings)
    return [f for f in findings if not _muted(f)]


def format_github(findings: list[Finding], *, show_suppressed: bool = False) -> str:
    """GitHub Actions ``::error`` / ``::warning`` annotations, one per finding.

    Baselined findings are downgraded to ``::notice`` so they inform without
    cluttering the PR.
    """
    lines: list[str] = []
    for f in _reportable(findings, show_suppressed=show_suppressed):
        level = "notice" if f.baselined else _GH_LEVEL.get(f.severity.value, "warning")
        msg = f.description.replace("\n", " ").replace("::", ":")
        title = f"{f.rule_id}: {f.title}"
        lines.append(
            f"::{level} file={f.location.file},line={f.location.line},"
            f"col={f.location.col},title={title}::{msg}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


# ---------------------------------------------------------------------------
# Reviewdog Diagnostic JSON (rdjson)
# ---------------------------------------------------------------------------

_RDJSON_SEVERITY = {
    "critical": "ERROR",
    "high": "ERROR",
    "medium": "WARNING",
    "low": "INFO",
    "info": "INFO",
}


def format_rdjson(
    findings: list[Finding], *, show_suppressed: bool = False, tool_version: str = "0.0.0"
) -> str:
    """Reviewdog Diagnostic Result Format -- for inline PR comments via reviewdog."""
    diagnostics = []
    for f in _reportable(findings, show_suppressed=show_suppressed):
        rng: dict[str, Any] = {"start": {"line": f.location.line, "column": f.location.col}}
        if f.location.end_line is not None and f.location.end_col is not None:
            rng["end"] = {"line": f.location.end_line, "column": f.location.end_col}
        diagnostics.append(
            {
                "message": f"{f.title}\n{f.description}"
                + (f"\n\nFix: {f.fix_suggestion}" if f.fix_suggestion else ""),
                "location": {"path": f.location.file, "range": rng},
                "severity": "INFO"
                if f.baselined
                else _RDJSON_SEVERITY.get(f.severity.value, "WARNING"),
                "code": {"value": f.rule_id, "url": finding_help_uri(f.rule_id)},
            }
        )
    return json.dumps(
        {
            "source": {
                "name": "codeguard",
                "url": "https://github.com/mevichitra/codeguard",
            },
            "diagnostics": diagnostics,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# JUnit XML
# ---------------------------------------------------------------------------


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def format_junit(findings: list[Finding], *, show_suppressed: bool = False) -> str:
    """JUnit XML -- one ``<testcase>`` per finding, so CI dashboards can chart them."""
    active = _reportable(findings, show_suppressed=show_suppressed)
    gating = [f for f in active if not f.baselined]
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<testsuites name="codeguard" tests="{len(active)}" failures="{len(gating)}">',
        f'  <testsuite name="codeguard" tests="{len(active)}" failures="{len(gating)}">',
    ]
    for f in active:
        loc = f"{f.location.file}:{f.location.line}:{f.location.col}"
        name = _xml_escape(f"{f.rule_id} {loc}")
        if f.baselined:
            parts.append(f'    <testcase name="{name}" classname="{f.rule_id}">')
            parts.append(f'      <skipped message="{_xml_escape(f.title)} (baselined)"/>')
            parts.append("    </testcase>")
        else:
            parts.append(f'    <testcase name="{name}" classname="{f.rule_id}">')
            parts.append(
                f'      <failure message="{_xml_escape(f.title)}" '
                f'type="{f.severity.value}">{_xml_escape(f.description)}</failure>'
            )
            parts.append("    </testcase>")
    parts.append("  </testsuite>")
    parts.append("</testsuites>")
    return "\n".join(parts) + "\n"
