# SPDX-License-Identifier: Apache-2.0
"""The ``codeguard/summary`` payload: workspace findings grouped for editor UIs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from codeguard.cli.formatters import finding_help_uri
from codeguard.engine.finding import Finding

SEVERITIES = ("critical", "high", "medium", "low", "info")
SUMMARY_SCHEMA_VERSION = 1


def _active(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if not f.suppressed and not f.baselined]


def counts(findings_by_uri: Mapping[str, list[Finding]]) -> dict[str, Any]:
    """Severity / category totals across every published document."""
    every = [f for fs in findings_by_uri.values() for f in fs]
    active = _active(every)
    by_sev = Counter(f.severity.value for f in active)
    by_cat = Counter(f.category.value for f in active)
    return {
        "total": len(active),
        "bySeverity": {s: by_sev.get(s, 0) for s in SEVERITIES},
        "byCategory": dict(sorted(by_cat.items())),
        "fixable": sum(1 for f in active if f.fix is not None and f.fix.safe),
        "suppressed": sum(1 for f in every if f.suppressed),
        "baselined": sum(1 for f in every if f.baselined and not f.suppressed),
        "files": sum(1 for fs in findings_by_uri.values() if _active(fs)),
    }


def build_summary(
    findings_by_uri: Mapping[str, list[Finding]],
    root: Path,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Everything an editor panel needs to render the workspace's findings."""
    files: list[dict[str, Any]] = []
    rules: dict[str, dict[str, Any]] = {}
    for uri, findings in sorted(findings_by_uri.items()):
        active = _active(findings)
        if not active:
            continue
        rows = []
        for f in sorted(active, key=lambda x: (x.location.line, x.location.col, x.rule_id)):
            has_fix = f.fix is not None and f.fix.safe
            rows.append(
                {
                    "ruleId": f.rule_id,
                    "title": f.title,
                    "description": f.description,
                    "severity": f.severity.value,
                    "category": f.category.value,
                    "line": f.location.line,
                    "col": f.location.col,
                    "endLine": f.location.end_line,
                    "endCol": f.location.end_col,
                    "fingerprint": f.fingerprint,
                    "hasFix": has_fix,
                    "cwe": f.cwe,
                    "helpUri": finding_help_uri(f.rule_id),
                    "confidence": f.confidence,
                }
            )
            entry = rules.setdefault(
                f.rule_id,
                {
                    "id": f.rule_id,
                    "title": f.title,
                    "severity": f.severity.value,
                    "category": f.category.value,
                    "count": 0,
                    "hasFix": False,
                },
            )
            entry["count"] += 1
            entry["hasFix"] = entry["hasFix"] or has_fix
        sev = Counter(f.severity.value for f in active)
        files.append(
            {
                "uri": uri,
                "path": _display_path(findings[0].location.file, root),
                "counts": {
                    "total": len(active),
                    "bySeverity": {s: sev.get(s, 0) for s in SEVERITIES},
                },
                "findings": rows,
            }
        )
    generated = generated_at or datetime.now(timezone.utc)
    return {
        "schemaVersion": SUMMARY_SCHEMA_VERSION,
        "generatedAt": generated.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspaceRoot": str(root),
        "counts": counts(findings_by_uri),
        "files": files,
        "rules": sorted(rules.values(), key=lambda r: (-r["count"], r["id"])),
    }


def _display_path(file: str, root: Path) -> str:
    path = Path(file)
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return path.as_posix()
