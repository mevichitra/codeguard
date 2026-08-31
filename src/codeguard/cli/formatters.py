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

    Suppressed findings are omitted unless *show_suppressed* is True.
    """
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=True)

    active = [f for f in findings if not f.suppressed]
    suppressed = [f for f in findings if f.suppressed]

    if not active and not (show_suppressed and suppressed):
        console.print("[bold green]✓ No findings.[/bold green]")
        return buf.getvalue()

    _file_cache: dict[str, list[str]] = {}

    for f in active:
        color = _SEVERITY_COLOR.get(f.severity.value, "white")
        loc = f"{f.location.file}:{f.location.line}:{f.location.col}"
        sev = f.severity.value.upper()
        console.print(f"[dim]{loc}[/dim]  [{color}][{f.rule_id}] {sev}[/{color}]  {f.title}")

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

    if show_suppressed and suppressed:
        console.print(f"\n[dim]{len(suppressed)} suppressed finding(s)[/dim]")

    _print_summary(console, active)
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
    emitted = findings if show_suppressed else [f for f in findings if not f.suppressed]

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
    emitted = findings if show_suppressed else [f for f in findings if not f.suppressed]
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
