# SPDX-License-Identifier: Apache-2.0
"""Pure builders for the language server: settings, diagnostics, code actions, hovers.

Kept free of I/O and threading so each piece is easy to test on its own.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from codeguard.cli.formatters import finding_help_uri
from codeguard.engine.finding import Finding
from codeguard.engine.fixes import edits_for, select_non_overlapping
from codeguard.lang.registry import language_for_path, support_for

from .positions import LineIndex, LspRange, overlaps

SOURCE = "CodeGuard"
FIX_ALL_KIND = "source.fixAll.codeguard"
DASHBOARD_KIND = "source.codeguard.dashboard"

#: Commands the server executes (``workspace/executeCommand``).  Namespaced so they
#: never collide with the VS Code extension's own palette commands.
CMD_OPEN_DASHBOARD = "codeguard.lsp.openDashboard"
CMD_EXPLAIN = "codeguard.lsp.explain"
CMD_SCAN_WORKSPACE = "codeguard.lsp.scanWorkspace"
CMD_FIX_ALL = "codeguard.lsp.fixAll"
COMMANDS = [CMD_OPEN_DASHBOARD, CMD_EXPLAIN, CMD_SCAN_WORKSPACE, CMD_FIX_ALL]

#: LSP DiagnosticSeverity; 0 means "do not publish".
_SEVERITY_NAMES = {"error": 1, "warning": 2, "information": 3, "info": 3, "hint": 4, "off": 0}
DEFAULT_SEVERITY_MAP: Mapping[str, int] = {
    "critical": 1,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}
_CATEGORY_NAMES = frozenset({"security", "performance", "quality"})
_REASON = "reason: <why this is safe>"
_SEVERITY_BADGE = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}


@dataclass(frozen=True)
class Settings:
    """Editor settings, from ``initializationOptions`` or ``didChangeConfiguration``.

    Shape (both clients send the same keys)::

        {"severityMap": {"medium": "error"}, "categories": {"quality": false},
         "rules": {"disable": ["CG-QUAL-104"]}, "scanWorkspaceOnStartup": true,
         "codeDescription": "help" | "dashboard", "client": "vscode" | "zed"}
    """

    severity_map: Mapping[str, int] = field(default_factory=lambda: dict(DEFAULT_SEVERITY_MAP))
    category_overrides: tuple[tuple[str, bool], ...] = ()
    disabled_rules: tuple[str, ...] = ()
    scan_on_startup: bool = True
    code_description: str = "help"
    client: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None, *, base: Settings | None = None) -> Settings:
        """Parse *data*, ignoring unknown keys and malformed values."""
        base = base or cls()
        if not isinstance(data, Mapping):
            return base
        severity_map = dict(base.severity_map)
        raw_map = data.get("severityMap")
        if isinstance(raw_map, Mapping):
            for sev, value in raw_map.items():
                level = _parse_level(value)
                if sev in DEFAULT_SEVERITY_MAP and level is not None:
                    severity_map[sev] = level
        overrides = base.category_overrides
        raw_cats = data.get("categories")
        if isinstance(raw_cats, Mapping):
            overrides = tuple(
                (str(k), bool(v))
                for k, v in raw_cats.items()
                if k in _CATEGORY_NAMES and isinstance(v, bool)
            )
        elif isinstance(raw_cats, list):
            wanted = {c for c in raw_cats if c in _CATEGORY_NAMES}
            overrides = tuple((c, c in wanted) for c in sorted(_CATEGORY_NAMES))
        disabled = base.disabled_rules
        rules = data.get("rules")
        if isinstance(rules, Mapping) and isinstance(rules.get("disable"), list):
            disabled = tuple(str(r) for r in rules["disable"] if isinstance(r, str))
        scan = data.get("scanWorkspaceOnStartup", base.scan_on_startup)
        description = data.get("codeDescription", base.code_description)
        client = data.get("client", base.client)
        return cls(
            severity_map=severity_map,
            category_overrides=overrides,
            disabled_rules=disabled,
            scan_on_startup=scan if isinstance(scan, bool) else base.scan_on_startup,
            code_description=description if description in ("help", "dashboard") else "help",
            client=str(client) if isinstance(client, str) else base.client,
        )


def _parse_level(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 0 <= value <= 4:
        return value
    if isinstance(value, str):
        return _SEVERITY_NAMES.get(value.lower())
    return None


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def lsp_severity(finding: Finding, settings: Settings) -> int:
    return int(settings.severity_map.get(finding.severity.value, 2))


def finding_to_diagnostic(
    finding: Finding,
    *,
    index: LineIndex | None = None,
    settings: Settings | None = None,
    dashboard_uri: str | None = None,
    uri_for: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """A native LSP ``Diagnostic`` for *finding*.

    ``data`` carries the fingerprint and the fix (as LSP text edits) so code
    actions need no re-analysis.
    """
    settings = settings or Settings()
    index = index or LineIndex("")
    message = f"🛡 {finding.title}\n{finding.description}"
    if finding.fix_suggestion:
        message += f"\n\nFix: {finding.fix_suggestion}"
    href = (
        dashboard_uri
        if settings.code_description == "dashboard" and dashboard_uri
        else finding_help_uri(finding.rule_id)
    )
    has_fix = finding.fix is not None and finding.fix.safe
    data: dict[str, Any] = {
        "fingerprint": finding.fingerprint,
        "ruleId": finding.rule_id,
        "category": finding.category.value,
        "severity": finding.severity.value,
        "hasFix": has_fix,
    }
    if has_fix and finding.fix is not None:
        data["fix"] = {
            "title": finding.fix.description,
            "edits": [index.text_edit(e) for e in finding.fix.edits],
        }
    diagnostic: dict[str, Any] = {
        "range": index.location_range(finding.location),
        "severity": lsp_severity(finding, settings) or 2,
        "code": finding.rule_id,
        "codeDescription": {"href": href},
        "source": SOURCE,
        "message": message,
        "data": data,
    }
    if finding.related:
        same_file_uri = (uri_for or {}).get(finding.location.file)
        info = []
        for rel in finding.related:
            uri = (uri_for or {}).get(rel.location.file) or same_file_uri
            if uri is None:
                uri = Path(rel.location.file).resolve().as_uri()
            info.append(
                {
                    "location": {"uri": uri, "range": index.location_range(rel.location)},
                    "message": rel.message,
                }
            )
        diagnostic["relatedInformation"] = info
    return diagnostic


# ---------------------------------------------------------------------------
# Code actions
# ---------------------------------------------------------------------------


def _comment_token(path: Path) -> str:
    language = language_for_path(path)
    if language is None:
        return "#"
    prefixes = support_for(language).comment_prefixes
    return prefixes[0] if prefixes else "#"


_IGNORE_RE = re.compile(r"codeguard:\s*ignore\[([^\]]*)\]")


def suppress_line_edit(finding: Finding, index: LineIndex, path: Path) -> dict[str, Any] | None:
    """Edit adding ``codeguard: ignore[ID]`` on the finding's line (or extending one)."""
    line_no = finding.location.line - 1
    text = index.line(line_no)
    match = _IGNORE_RE.search(text)
    if match is not None:
        ids = [i.strip() for i in match.group(1).split(",") if i.strip()]
        if finding.rule_id in ids:
            return None
        utf16 = len(text[: match.end(1)].encode("utf-16-le")) // 2
        pos = {"line": line_no, "character": utf16}
        return {"range": {"start": pos, "end": pos}, "newText": f", {finding.rule_id}"}
    token = _comment_token(path)
    end = index.line_end(line_no)
    return {
        "range": {"start": end, "end": end},
        "newText": f"  {token} codeguard: ignore[{finding.rule_id}] {_REASON}",
    }


def suppress_file_edit(finding: Finding, index: LineIndex, path: Path) -> dict[str, Any]:
    """Edit adding ``codeguard: ignore-file[ID]`` at the top (after shebang / coding lines)."""
    line = 0
    while line < 2 and (
        index.line(line).startswith("#!") or re.match(r"^#.*coding[:=]", index.line(line))
    ):
        line += 1
    token = _comment_token(path)
    pos = {"line": line, "character": 0}
    return {
        "range": {"start": pos, "end": pos},
        "newText": f"{token} codeguard: ignore-file[{finding.rule_id}] {_REASON}\n",
    }


def code_actions(
    uri: str,
    path: Path,
    findings: Sequence[Finding],
    index: LineIndex,
    source: str,
    request_range: LspRange,
    only: Sequence[str] | None,
) -> list[dict[str, Any]]:
    """Quick fixes, suppressions, and explain for findings under *request_range*,
    plus a fix-all source action for the document."""
    actions: list[dict[str, Any]] = []
    want_quickfix = not only or any(k == "quickfix" or "quickfix".startswith(k) for k in only)
    want_fix_all = not only or any(FIX_ALL_KIND.startswith(k) for k in only)
    active = [f for f in findings if not f.suppressed and not f.baselined]

    if want_quickfix:
        for finding in active:
            rng = index.location_range(finding.location)
            if not overlaps(rng, request_range):
                continue
            diagnostic = {
                "range": rng,
                "code": finding.rule_id,
                "source": SOURCE,
                "message": finding.title,
            }
            if finding.fix is not None and finding.fix.safe:
                actions.append(
                    {
                        "title": f"Fix: {finding.fix.description} ({finding.rule_id})",
                        "kind": "quickfix",
                        "isPreferred": True,
                        "diagnostics": [diagnostic],
                        "edit": {"changes": {uri: [index.text_edit(e) for e in finding.fix.edits]}},
                    }
                )
            line_edit = suppress_line_edit(finding, index, path)
            if line_edit is not None:
                actions.append(
                    {
                        "title": f"Suppress {finding.rule_id} on this line",
                        "kind": "quickfix",
                        "diagnostics": [diagnostic],
                        "edit": {"changes": {uri: [line_edit]}},
                    }
                )
            actions.append(
                {
                    "title": f"Suppress {finding.rule_id} in this file",
                    "kind": "quickfix",
                    "diagnostics": [diagnostic],
                    "edit": {"changes": {uri: [suppress_file_edit(finding, index, path)]}},
                }
            )
            actions.append(
                {
                    "title": f"Explain {finding.rule_id}: {finding.title}",
                    "kind": "quickfix",
                    "diagnostics": [diagnostic],
                    "command": {
                        "title": f"Explain {finding.rule_id}",
                        "command": CMD_EXPLAIN,
                        "arguments": [finding.rule_id],
                    },
                }
            )

    if want_fix_all:
        edits = fix_all_edits(source, active, index)
        if edits:
            actions.append(
                {
                    "title": f"Fix all CodeGuard issues in this file ({len(edits)} safe edit"
                    f"{'s' if len(edits) != 1 else ''})",
                    "kind": FIX_ALL_KIND,
                    "edit": {"changes": {uri: edits}},
                }
            )
    return actions


def fix_all_edits(
    source: str, findings: Sequence[Finding], index: LineIndex
) -> list[dict[str, Any]]:
    """Non-overlapping LSP text edits for every safe fix in *findings*."""
    accepted, _skipped = select_non_overlapping(source, findings)
    return [index.text_edit(e) for e in edits_for(accepted)]


# ---------------------------------------------------------------------------
# Hover
# ---------------------------------------------------------------------------


def hover_markdown(finding: Finding) -> str:
    sev = finding.severity.value
    lines = [
        f"**{finding.rule_id} · {finding.title}**",
        "",
        f"{_SEVERITY_BADGE.get(sev, '')} `{sev.upper()}` · {finding.category.value}"
        + (f" · confidence {finding.confidence:.0%}" if finding.confidence < 1.0 else ""),
        "",
        finding.description,
    ]
    refs = []
    if finding.cwe:
        number = finding.cwe.split("-")[-1]
        refs.append(f"[{finding.cwe}](https://cwe.mitre.org/data/definitions/{number}.html)")
    if finding.owasp:
        refs.append(f"OWASP {finding.owasp}")
    if refs:
        lines += ["", " · ".join(refs)]
    if finding.related:
        lines += ["", "**Data flow**", ""]
        lines += [f"- line {r.location.line}: `{r.message}`" for r in finding.related]
    if finding.fix is not None and finding.fix.safe:
        lines += ["", f"**Quick fix available:** {finding.fix.description}"]
    if finding.fix_suggestion:
        lines += ["", f"**How to fix:** {finding.fix_suggestion}"]
    lines += [
        "",
        f"[Rule documentation]({finding_help_uri(finding.rule_id)}) · suppress with "
        f"`codeguard: ignore[{finding.rule_id}] reason: …`",
    ]
    return "\n".join(lines)
