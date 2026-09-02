# SPDX-License-Identifier: Apache-2.0
"""Generate a local Markdown dashboard for editor integrations."""

from __future__ import annotations

import hashlib
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from platformdirs import user_cache_path

from codeguard.cli.formatters import finding_help_uri
from codeguard.engine.finding import Finding

_SEVERITIES = ("critical", "high", "medium", "low", "info")
_SEVERITY_ICON = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}


def dashboard_path(workspace_root: Path) -> Path:
    """Return a stable cache path for one workspace's generated report."""
    root = str(workspace_root.resolve())
    workspace_id = hashlib.sha256(root.encode("utf-8")).hexdigest()[:12]
    return user_cache_path("codeguard") / "dashboards" / workspace_id / "report.md"


def render_dashboard(
    findings: list[Finding],
    workspace_root: Path,
    *,
    generated_at: datetime | None = None,
) -> str:
    """Render findings as a self-contained Markdown dashboard."""
    root = workspace_root.resolve()
    generated = generated_at or datetime.now(timezone.utc)
    active = [item for item in findings if not item.suppressed and not item.baselined]
    suppressed = [item for item in findings if item.suppressed]
    baselined = [item for item in findings if item.baselined and not item.suppressed]
    counts = Counter(item.severity.value for item in active)

    lines = [
        "# 🛡️ CodeGuard Dashboard",
        "",
        f"**Workspace:** `{_escape_inline(str(root))}`  ",
        f"**Generated:** {generated.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        "**Privacy:** generated locally; source code was not uploaded.",
        "",
        "> In Zed, use **Markdown: Open Preview** (`Cmd+Shift+V`) for the rendered view.",
        "",
        "## Summary",
        "",
        "| Active | Baselined | Suppressed |",
        "| ---: | ---: | ---: |",
        f"| **{len(active)}** | {len(baselined)} | {len(suppressed)} |",
        "",
        "| Severity | Findings |",
        "| --- | ---: |",
    ]
    lines.extend(
        f"| {_SEVERITY_ICON[severity]} {severity.title()} | {counts.get(severity, 0)} |"
        for severity in _SEVERITIES
    )
    lines.extend(["", "## Active findings", ""])

    if not active:
        lines.extend(["✅ No active findings.", ""])
    else:
        lines.extend(
            [
                "| Severity | Rule | Location | Finding | Suggested fix |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for finding in active:
            location = _relative_location(finding, root)
            file_uri = Path(finding.location.file).resolve().as_uri()
            file_link = f"[{_escape_table(location)}]({file_uri}#L{finding.location.line})"
            rule_link = f"[{finding.rule_id}]({finding_help_uri(finding.rule_id)})"
            fix = _escape_table(finding.fix_suggestion or "—")
            lines.append(
                "| "
                f"{_SEVERITY_ICON[finding.severity.value]} {finding.severity.value.title()} | "
                f"{rule_link} | {file_link} | {_escape_table(finding.title)} | {fix} |"
            )
        lines.append("")

    if baselined or suppressed:
        lines.extend(["## Muted findings", ""])
        if baselined:
            lines.append(f"- **Baselined:** {len(baselined)}")
        if suppressed:
            lines.append(f"- **Suppressed:** {len(suppressed)}")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "Regenerate from the editor's **🛡 CodeGuard** link or run `codeguard dashboard`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_dashboard(
    findings: list[Finding],
    workspace_root: Path,
    *,
    output: Path | None = None,
) -> Path:
    """Write and return a dashboard path, defaulting to the user cache."""
    target = (output or dashboard_path(workspace_root)).resolve()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        if output is not None:
            raise
        target = (
            Path(tempfile.gettempdir())
            / "codeguard"
            / "dashboards"
            / hashlib.sha256(str(workspace_root.resolve()).encode("utf-8")).hexdigest()[:12]
            / "report.md"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_dashboard(findings, workspace_root), encoding="utf-8")
    return target


def _relative_location(finding: Finding, root: Path) -> str:
    path = Path(finding.location.file).resolve()
    try:
        display = path.relative_to(root).as_posix()
    except ValueError:
        display = path.as_posix()
    return f"{display}:{finding.location.line}:{finding.location.col}"


def _escape_inline(value: str) -> str:
    return value.replace("`", "\\`")


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
