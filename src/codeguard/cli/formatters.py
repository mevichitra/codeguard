# SPDX-License-Identifier: Apache-2.0
"""Output formatters: human-readable, JSON, and SARIF."""

from __future__ import annotations

import json
from typing import Any

from codeguard.engine.finding import Finding

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

        # Show the offending source line with a column marker
        try:
            if f.location.file not in _file_cache:
                with open(f.location.file, encoding="utf-8", errors="replace") as fh:
                    _file_cache[f.location.file] = fh.readlines()
            lines = _file_cache[f.location.file]
            line_idx = f.location.line - 1
            if 0 <= line_idx < len(lines):
                source = lines[line_idx].rstrip()
                line_no = f.location.line
                gutter = f"{line_no:>4}"
                console.print(f"  {gutter} | {source}", style="dim", markup=False)
                pointer = " " * (len(gutter) + 3 + f.location.col) + "^"
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
    from collections import Counter

    counts = Counter(f.severity.value for f in findings)
    total = len(findings)
    parts = []
    for sev in ("critical", "high", "medium", "low", "info"):
        n = counts.get(sev, 0)
        if n:
            color = _SEVERITY_COLOR[sev]
            parts.append(f"[{color}]{n} {sev}[/{color}]")
    summary = ", ".join(parts) if parts else "0"
    console.print(f"\n[bold]{total} finding(s)[/bold]  ({summary})")


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def format_json(findings: list[Finding], *, show_suppressed: bool = False) -> str:
    """Return findings serialised as a JSON array.

    Suppressed findings are included with ``"suppressed": true`` when
    *show_suppressed* is True; otherwise they are omitted.
    """
    to_emit = findings if show_suppressed else [f for f in findings if not f.suppressed]
    return json.dumps([f.to_dict() for f in to_emit], indent=2)


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


def format_sarif(findings: list[Finding], *, tool_version: str = "0.1.0") -> str:
    """Return findings as a SARIF 2.1.0 JSON string.

    SARIF is the standard format for static analysis results understood by
    GitHub code scanning and other tools.  See:
    https://docs.oasis-open.org/sarif/sarif/v2.1.0/

    Suppressed findings are included as ``"suppressions"`` entries per the spec.
    """
    # Build the set of rules referenced by these findings
    rule_map: dict[str, Finding] = {}
    for f in findings:
        if f.rule_id not in rule_map:
            rule_map[f.rule_id] = f

    rules = []
    for rule_id, f in sorted(rule_map.items()):
        rule: dict[str, Any] = {
            "id": rule_id,
            "name": f.title,
            "shortDescription": {"text": f.title},
            "fullDescription": {"text": f.description},
            "defaultConfiguration": {"level": _SARIF_SEVERITY.get(f.severity.value, "warning")},
            "properties": {
                "tags": [f.category.value],
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
        result: dict[str, Any] = {
            "ruleId": f.rule_id,
            "level": _SARIF_SEVERITY.get(f.severity.value, "warning"),
            "message": {"text": f.description},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.location.file, "uriBaseId": "%SRCROOT%"},
                        "region": {
                            "startLine": f.location.line,
                            "startColumn": f.location.col + 1,  # SARIF is 1-indexed
                            **(
                                {"endLine": f.location.end_line}
                                if f.location.end_line is not None
                                else {}
                            ),
                        },
                    }
                }
            ],
            "properties": {
                "confidence": f.confidence,
                "severity": f.severity.value,
            },
        }
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
                        "informationUri": "https://github.com/codeguard-ai/codeguard",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }

    return json.dumps(sarif, indent=2)
