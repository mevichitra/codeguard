#!/usr/bin/env python3
"""Run CodeGuard showcase demos and build a self-contained HTML report."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEMO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DEMO_DIR.parent
DEFAULT_OUTPUT = DEMO_DIR / "reports" / "codeguard-demo-report.html"

DEMOS = {
    "1": ("Developer Inner-Loop", DEMO_DIR / "01_developer_inner_loop" / "run.sh"),
    "2": ("Legacy Baseline Adoption", DEMO_DIR / "02_legacy_baseline" / "run.sh"),
    "3": ("Diff-Aware CI & SARIF", DEMO_DIR / "03_ci_diff_and_sarif" / "run.sh"),
    "4": ("Governed Suppressions", DEMO_DIR / "04_governed_suppressions" / "run.sh"),
    "5": ("Monorepo Policy", DEMO_DIR / "05_monorepo_policy" / "run.sh"),
}

DEMO_SCAN_FILES = {
    "1": [
        DEMO_DIR / "01_developer_inner_loop" / "app.py",
        DEMO_DIR / "01_developer_inner_loop" / "user_service.ts",
    ],
    "2": [DEMO_DIR / "02_legacy_baseline" / "legacy_service.py"],
    "3": [DEMO_DIR / "03_ci_diff_and_sarif" / "dirty_feature.py"],
    "4": [DEMO_DIR / "04_governed_suppressions" / "payments.py"],
    "5": [
        DEMO_DIR / "05_monorepo_policy" / "services" / "auth" / "auth_service.py",
        DEMO_DIR / "05_monorepo_policy" / "scripts" / "admin_tool.py",
    ],
}

DEMO_SCAN_CONFIG = {"5": DEMO_DIR / "05_monorepo_policy" / "codeguard.toml"}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

ANSI_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
SEPARATOR_RE = re.compile(r"^[=-]{20,}$")
STEP_RE = re.compile(r"^▶\s*STEP\s+\d+:\s*(.*)$")
TAKEAWAY_RE = re.compile(r"^\s*\d+\.\s*(.*)$")
FINDING_RE = re.compile(r"(?m)^\s*(\d+) finding\(s\)")


@dataclass
class Section:
    title: str
    body: str


@dataclass
class FindingItem:
    rule_id: str
    title: str
    description: str
    severity: str
    category: str
    file: str
    line: int
    col: int
    source_line: str
    fix_suggestion: str
    cwe: str
    owasp: str
    confidence: float
    suppressed: bool
    baselined: bool
    fingerprint: str


@dataclass
class DemoResult:
    number: str
    short_title: str
    title: str
    scenario: str
    sections: list[Section]
    takeaways: list[str]
    output: str
    returncode: int
    finding_count: int | None
    findings: list[FindingItem]


def clean_output(value: str) -> str:
    value = ANSI_RE.sub("", value).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in value.splitlines()).strip()


def codeguard_binary() -> str:
    local_binary = PROJECT_ROOT / ".venv" / "bin" / "codeguard"
    if local_binary.is_file():
        return str(local_binary)
    installed = shutil.which("codeguard")
    if installed:
        return installed
    raise RuntimeError("CodeGuard binary not found")


def source_line_for(file_name: str, line_number: int) -> str:
    path = Path(file_name)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    index = line_number - 1
    return lines[index] if 0 <= index < len(lines) else ""


def display_path(file_name: str) -> str:
    path = Path(file_name)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def collect_findings(number: str) -> list[FindingItem]:
    findings: list[FindingItem] = []
    binary = codeguard_binary()
    config = DEMO_SCAN_CONFIG.get(number)
    env = os.environ.copy()
    env.update({"NO_COLOR": "1", "TERM": "dumb"})

    for target in DEMO_SCAN_FILES[number]:
        command = [binary, "scan", str(target), "--format", "json", "--show-suppressed"]
        if config:
            command.extend(["--config", str(config)])
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        try:
            payload: dict[str, Any] = json.loads(completed.stdout)
        except json.JSONDecodeError:
            continue
        for raw in payload.get("results", []):
            location = raw.get("location", {})
            file_name = str(location.get("file", target))
            line = int(location.get("line", 1))
            findings.append(
                FindingItem(
                    rule_id=str(raw.get("rule_id", "Unknown rule")),
                    title=str(raw.get("title", "Untitled finding")),
                    description=str(raw.get("description", "")),
                    severity=str(raw.get("severity", "info")).lower(),
                    category=str(raw.get("category", "security")),
                    file=display_path(file_name),
                    line=line,
                    col=int(location.get("col", 1)),
                    source_line=source_line_for(file_name, line),
                    fix_suggestion=str(raw.get("fix_suggestion") or ""),
                    cwe=str(raw.get("cwe") or ""),
                    owasp=str(raw.get("owasp") or ""),
                    confidence=float(raw.get("confidence", 0)),
                    suppressed=bool(raw.get("suppressed", False)),
                    baselined=bool(raw.get("baselined", False)),
                    fingerprint=str(raw.get("fingerprint") or ""),
                )
            )

    findings.sort(key=lambda item: (SEVERITY_ORDER.get(item.severity, 99), item.file, item.line))
    return findings


def parse_output(number: str, short_title: str, output: str, returncode: int) -> DemoResult:
    lines = output.splitlines()
    title = f"Demo {number}: {short_title}"
    scenario = ""
    takeaways: list[str] = []
    sections: list[Section] = []
    current_title = "Scan results"
    current_lines: list[str] = []
    in_takeaways = False

    def flush_section() -> None:
        body_lines = list(current_lines)
        while body_lines and (not body_lines[0].strip() or SEPARATOR_RE.match(body_lines[0])):
            body_lines.pop(0)
        while body_lines and (not body_lines[-1].strip() or SEPARATOR_RE.match(body_lines[-1])):
            body_lines.pop()
        body = "\n".join(body_lines).strip()
        if body:
            sections.append(Section(current_title, body))

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("DEMO "):
            title = line
            continue
        if line.startswith("Scenario:"):
            scenario = line.removeprefix("Scenario:").strip()
            continue
        if "KEY TAKEAWAYS & VALUE PROPOSITION:" in line:
            flush_section()
            current_lines.clear()
            in_takeaways = True
            continue
        if in_takeaways:
            match = TAKEAWAY_RE.match(raw_line)
            if match:
                takeaways.append(match.group(1).strip())
            continue
        step_match = STEP_RE.match(line)
        if step_match:
            flush_section()
            current_lines.clear()
            current_title = step_match.group(1).strip()
            continue
        if SEPARATOR_RE.match(line) or (line.startswith("=") and line.endswith("=")):
            continue
        current_lines.append(raw_line)

    if not in_takeaways:
        flush_section()

    findings = [int(value) for value in FINDING_RE.findall(output)]
    return DemoResult(
        number=number,
        short_title=short_title,
        title=title,
        scenario=scenario,
        sections=sections,
        takeaways=takeaways,
        output=output,
        returncode=returncode,
        finding_count=max(findings) if findings else None,
        findings=[],
    )


def run_demo(number: str) -> DemoResult:
    short_title, script = DEMOS[number]
    env = os.environ.copy()
    env.update({"NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "120"})
    completed = subprocess.run(
        ["bash", str(script)],
        cwd=DEMO_DIR.parent,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    result = parse_output(number, short_title, clean_output(completed.stdout), completed.returncode)
    result.findings = collect_findings(number)
    result.finding_count = len([finding for finding in result.findings if not finding.suppressed])
    return result


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def finding_status(finding: FindingItem) -> tuple[str, str]:
    if finding.suppressed:
        return "Suppressed", "suppressed"
    if finding.baselined:
        return "Baselined", "baselined"
    return "Active", "active"


def render_finding(finding: FindingItem, demo_number: str, index: int) -> str:
    status_label, status_class = finding_status(finding)
    anchor = f"demo-{demo_number}-finding-{index}"
    pointer = " " * max(finding.col - 1, 0) + "^"
    taxonomy = "".join(
        f'<span class="taxonomy">{esc(value)}</span>'
        for value in (finding.cwe, finding.owasp, finding.category.title())
        if value
    )
    fix_html = (
        f'<div class="fix"><span class="fix-icon">→</span><div><strong>Recommended fix</strong><p>{esc(finding.fix_suggestion)}</p></div></div>'
        if finding.fix_suggestion
        else ""
    )
    source_html = ""
    if finding.source_line:
        source_html = f"""
        <div class="source-block">
          <div class="source-location">{esc(finding.file)}:{finding.line}:{finding.col}</div>
          <pre><code><span class="line-number">{finding.line}</span> {esc(finding.source_line)}
<span class="line-number"> </span> {esc(pointer)}</code></pre>
        </div>"""
    search_text = " ".join(
        (finding.rule_id, finding.title, finding.description, finding.file, finding.cwe, finding.owasp)
    ).lower()
    return f"""
    <article class="finding-card" id="{anchor}" data-severity="{esc(finding.severity)}"
      data-status="{status_class}" data-search="{esc(search_text)}">
      <div class="finding-body">
        <div class="finding-topline">
          <div class="finding-ident"><span class="finding-index">{index:02d}</span><span class="rule-id">{esc(finding.rule_id)}</span></div>
          <div class="finding-labels"><span class="severity severity-{esc(finding.severity)}">{esc(finding.severity.upper())}</span><span class="status {status_class}">{status_label}</span></div>
        </div>
        <h4>{esc(finding.title)}</h4>
        <p class="finding-description">{esc(finding.description)}</p>
        {source_html}
        {fix_html}
        <div class="finding-footer"><div>{taxonomy}</div><span>{round(finding.confidence * 100)}% confidence</span></div>
      </div>
    </article>"""


def render_findings(result: DemoResult) -> str:
    if not result.findings:
        return '<section class="finding-report empty"><h3>Individual scan findings</h3><p>No structured findings were returned for this showcase.</p></section>'

    active_count = sum(not item.suppressed and not item.baselined for item in result.findings)
    suppressed_count = sum(item.suppressed for item in result.findings)
    critical_count = sum(item.severity == "critical" for item in result.findings)
    high_count = sum(item.severity == "high" for item in result.findings)
    cards = "".join(
        render_finding(finding, result.number, index)
        for index, finding in enumerate(result.findings, start=1)
    )
    filters = [
        ("all", f"All {len(result.findings)}"),
        ("active", f"Active {active_count}"),
    ]
    if critical_count:
        filters.append(("critical", f"Critical {critical_count}"))
    if high_count:
        filters.append(("high", f"High {high_count}"))
    if suppressed_count:
        filters.append(("suppressed", f"Suppressed {suppressed_count}"))
    filter_html = "".join(
        f'<button type="button" class="filter-chip{(" selected" if key == "all" else "")}" data-filter="{key}">{label}</button>'
        for key, label in filters
    )
    jump_options = "".join(
        f'<option value="#demo-{result.number}-finding-{index}">{index:02d} · {esc(finding.rule_id)} · {esc(Path(finding.file).name)}:{finding.line}</option>'
        for index, finding in enumerate(result.findings, start=1)
    )
    return f"""
    <section class="finding-report" id="demo-{result.number}-findings" data-demo="{result.number}">
      <div class="finding-report-heading">
        <div><span class="eyebrow">Scan report</span><h3>Individual findings</h3><p>Review each issue, the affected line, and the recommended remediation.</p></div>
        <div class="finding-total"><strong>{len(result.findings)}</strong><span>items</span></div>
      </div>
      <div class="finding-toolbar">
        <div class="filter-chips" aria-label="Filter findings">{filter_html}</div>
        <div class="finding-controls">
          <label class="finding-jump"><span>Jump to</span><select aria-label="Jump to finding"><option value="">Choose an item…</option>{jump_options}</select></label>
          <label class="finding-search"><span>Search</span><input type="search" placeholder="Rule, file, or issue…" aria-label="Search findings"></label>
        </div>
      </div>
      <p class="filter-empty" hidden>No findings match this filter.</p>
      <div class="finding-list">{cards}</div>
    </section>"""


def render_demo(result: DemoResult) -> str:
    status = "Completed" if result.returncode == 0 else f"Exited {result.returncode}"
    finding_badge = (
        f'<span class="badge finding">Up to {result.finding_count} active findings</span>'
        if result.finding_count is not None
        else ""
    )
    section_html = []
    for index, section in enumerate(result.sections, start=1):
        body_lines = section.body.splitlines()
        description: list[str] = []
        evidence: list[str] = []
        command = ""
        for line in body_lines:
            stripped = line.strip()
            if stripped.startswith("Command:"):
                command = stripped.removeprefix("Command:").strip()
            elif command or stripped.startswith(("/", "::", "{", "[", "<")):
                evidence.append(line)
            elif stripped:
                description.append(stripped)
        if not evidence and len(description) > 3:
            evidence = description[2:]
            description = description[:2]
        description_html = "".join(f"<p>{esc(line)}</p>" for line in description)
        command_html = f'<div class="command"><span>$</span> {esc(command)}</div>' if command else ""
        evidence_text = "\n".join(evidence).strip()
        evidence_html = (
            f'<pre class="evidence"><code>{esc(evidence_text)}</code></pre>' if evidence_text else ""
        )
        section_html.append(
            f"""
            <article class="step">
              <div class="step-number">{index:02d}</div>
              <div class="step-content">
                <h3>{esc(section.title)}</h3>
                {description_html}{command_html}{evidence_html}
              </div>
            </article>"""
        )

    takeaway_html = "".join(
        f'<li><span class="check">✓</span><span>{esc(item)}</span></li>' for item in result.takeaways
    )
    return f"""
    <section class="demo" id="demo-{result.number}">
      <div class="demo-heading">
        <div><span class="eyebrow">Showcase {result.number}</span><h2>{esc(result.title)}</h2></div>
        <div class="badges"><span class="badge success">{esc(status)}</span>{finding_badge}</div>
      </div>
      {f'<p class="scenario">{esc(result.scenario)}</p>' if result.scenario else ''}
      {render_findings(result)}
      <div class="section-divider"><span>Demo walkthrough</span></div>
      <div class="steps">{''.join(section_html)}</div>
      {f'<aside class="takeaways"><h3>Why it matters</h3><ul>{takeaway_html}</ul></aside>' if takeaway_html else ''}
      <details class="raw-output">
        <summary>View complete console evidence</summary>
        <pre><code>{esc(result.output)}</code></pre>
      </details>
    </section>"""


def render_report(results: list[DemoResult], generated_at: datetime) -> str:
    nav_parts = []
    for result in results:
        finding_links = "".join(
            f'<a class="nav-finding" href="#demo-{result.number}-finding-{index}"><i class="severity-{esc(finding.severity)}"></i><span>{esc(finding.rule_id)} · {esc(Path(finding.file).name)}:{finding.line}</span></a>'
            for index, finding in enumerate(result.findings, start=1)
        )
        nav_parts.append(
            f"""
            <div class="nav-demo">
              <a class="nav-demo-link" href="#demo-{result.number}"><b>{result.number}</b><span>{esc(result.short_title)}</span></a>
              <a class="nav-report-link" href="#demo-{result.number}-findings">Scan report <em>{len(result.findings)}</em></a>
              <div class="nav-finding-list">{finding_links}</div>
            </div>"""
        )
    nav = "".join(nav_parts)
    demos = "".join(render_demo(result) for result in results)
    all_findings = [finding for result in results for finding in result.findings]
    active_findings = sum(not finding.suppressed and not finding.baselined for finding in all_findings)
    high_risk = sum(finding.severity in {"critical", "high"} for finding in all_findings)
    suppressed = sum(finding.suppressed or finding.baselined for finding in all_findings)
    generated_label = generated_at.astimezone().strftime("%B %d, %Y at %I:%M %p %Z")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CodeGuard Showcase Report</title>
  <style>
    :root {{ --ink:#15211d; --muted:#66756e; --paper:#f5f3ec; --card:#fffefa;
      --green:#0f6b4f; --mint:#dcefe6; --gold:#d99a2b; --line:#d9ddd6; --code:#12221c; }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; color:var(--ink); background:var(--paper); font:16px/1.55 Inter, ui-sans-serif, system-ui, sans-serif; }}
    .hero {{ color:white; background:radial-gradient(circle at 82% 10%, #2b8b68 0, transparent 28%), linear-gradient(135deg,#10261e,#174d3b); padding:72px max(24px,calc((100vw - 1120px)/2)) 64px; }}
    .brand {{ display:flex; align-items:center; gap:12px; font-weight:750; letter-spacing:.03em; }}
    .brand-mark {{ display:grid; place-items:center; width:36px; height:36px; border:1px solid #7bc6a9; border-radius:10px; color:#b9f2dc; }}
    .hero-grid {{ display:grid; grid-template-columns:1.5fr .8fr; gap:64px; align-items:end; margin-top:60px; }}
    h1 {{ max-width:760px; margin:0; font-size:clamp(42px,7vw,78px); line-height:.96; letter-spacing:-.055em; }}
    .hero p {{ max-width:680px; margin:24px 0 0; color:#c8ddd4; font-size:19px; }}
    .scorecard {{ display:grid; grid-template-columns:1fr 1fr; gap:1px; overflow:hidden; border:1px solid #507464; border-radius:16px; background:#507464; }}
    .scorecard div {{ padding:20px; background:#173a2d; }} .scorecard strong {{ display:block; font-size:28px; }}
    .scorecard span {{ color:#a9c5b9; font-size:13px; text-transform:uppercase; letter-spacing:.09em; }}
    .layout {{ display:grid; grid-template-columns:260px minmax(0,1fr); gap:48px; max-width:1200px; margin:0 auto; padding:50px 24px 96px; }}
    .layout > *, .demo, .demo-heading > div, .step-content {{ min-width:0; }}
    nav {{ position:sticky; top:20px; align-self:start; max-width:100%; max-height:calc(100vh - 40px); overflow:auto; padding-right:8px; }} nav > small {{ display:block; margin-bottom:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.12em; }}
    nav a {{ color:var(--ink); text-decoration:none; }} .nav-demo {{ margin-bottom:10px; border-bottom:1px solid var(--line); padding-bottom:10px; }}
    .nav-demo-link {{ display:flex; gap:10px; align-items:center; padding:8px; border-radius:10px; font-size:14px; font-weight:700; }} .nav-demo-link:hover,.nav-report-link:hover,.nav-finding:hover {{ background:#e7eae4; }}
    .nav-demo-link b {{ display:grid; place-items:center; flex:0 0 28px; height:28px; border-radius:8px; background:var(--mint); color:var(--green); }}
    .nav-report-link {{ display:flex; justify-content:space-between; margin:2px 0 2px 46px; padding:5px 8px; border-radius:7px; color:var(--green); font-size:12px; font-weight:750; }} .nav-report-link em {{ min-width:22px; padding:1px 6px; border-radius:999px; background:var(--mint); text-align:center; font-style:normal; }}
    .nav-finding-list {{ margin-left:46px; }} .nav-finding {{ display:flex; align-items:center; gap:7px; padding:4px 8px; border-radius:6px; color:var(--muted); font-size:11px; }} .nav-finding span {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }} .nav-finding i {{ flex:0 0 7px; width:7px; height:7px; border-radius:50%; }}
    .demo {{ margin-bottom:72px; scroll-margin-top:24px; }} .demo-heading {{ display:flex; justify-content:space-between; gap:24px; align-items:start; }}
    .eyebrow {{ color:var(--green); font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.13em; }}
    h2 {{ margin:6px 0 0; overflow-wrap:anywhere; font-size:clamp(28px,4vw,42px); line-height:1.08; letter-spacing:-.035em; }}
    .scenario {{ max-width:760px; color:var(--muted); font-size:18px; }} .badges {{ display:flex; flex-wrap:wrap; justify-content:end; gap:8px; }}
    .badge {{ white-space:nowrap; padding:7px 10px; border-radius:999px; font-size:12px; font-weight:750; }}
    .badge.success {{ background:var(--mint); color:var(--green); }} .badge.finding {{ background:#fff0d5; color:#7c520b; }}
    .finding-report {{ margin-top:34px; padding:28px; border:1px solid var(--line); border-radius:20px; background:#e9ece7; scroll-margin-top:20px; }}
    .finding-report-heading {{ display:flex; justify-content:space-between; gap:24px; align-items:end; }} .finding-report-heading h3 {{ margin:3px 0; font-size:28px; letter-spacing:-.025em; }} .finding-report-heading p {{ margin:0; color:var(--muted); }}
    .finding-total {{ flex:0 0 78px; padding:12px; border-radius:14px; color:white; background:var(--green); text-align:center; }} .finding-total strong {{ display:block; font-size:26px; line-height:1; }} .finding-total span {{ font-size:11px; text-transform:uppercase; letter-spacing:.1em; }}
    .finding-toolbar {{ display:flex; justify-content:space-between; gap:16px; align-items:center; margin:22px 0 16px; }} .filter-chips {{ display:flex; flex-wrap:wrap; gap:7px; }}
    .filter-chip {{ border:1px solid #c8cec8; border-radius:999px; padding:7px 11px; color:var(--muted); background:#f8f8f4; cursor:pointer; font:700 12px/1 system-ui,sans-serif; }} .filter-chip:hover,.filter-chip.selected {{ border-color:var(--green); color:white; background:var(--green); }}
    .finding-controls {{ display:flex; flex-wrap:wrap; justify-content:end; gap:10px; }} .finding-search,.finding-jump {{ display:flex; align-items:center; gap:8px; color:var(--muted); font-size:12px; }} .finding-search input,.finding-jump select {{ width:190px; border:1px solid #c8cec8; border-radius:9px; padding:9px 11px; color:var(--ink); background:white; font:13px system-ui,sans-serif; }} .finding-search input:focus,.finding-jump select:focus {{ outline:2px solid #70b99e; outline-offset:1px; }}
    .finding-list {{ display:grid; gap:14px; }} .finding-card {{ position:relative; overflow:hidden; border:1px solid var(--line); border-radius:15px; background:var(--card); scroll-margin-top:20px; box-shadow:0 5px 20px rgba(30,48,40,.04); }} .finding-card[hidden] {{ display:none; }}
    .severity-critical {{ background:#9d1736; }} .severity-high {{ background:#d94b3d; }} .severity-medium {{ background:#d99a2b; }} .severity-low {{ background:#3978ad; }} .severity-info {{ background:#75847d; }}
    .finding-body {{ min-width:0; padding:21px 22px; }} .finding-topline {{ display:flex; justify-content:space-between; gap:16px; align-items:center; }} .finding-ident,.finding-labels {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; }}
    .finding-index {{ color:#93a099; font:700 12px ui-monospace,monospace; }} .rule-id {{ font:800 13px ui-monospace,monospace; }} .severity,.status,.taxonomy {{ display:inline-block; border-radius:999px; padding:4px 8px; font-size:10px; font-weight:850; letter-spacing:.06em; }}
    .severity {{ color:white; }} .status {{ color:#526059; background:#e6e9e5; }} .status.suppressed {{ color:#655013; background:#f3e8be; }} .status.baselined {{ color:#315a77; background:#dceaf3; }}
    .finding-card h4 {{ margin:14px 0 6px; font-size:21px; letter-spacing:-.015em; }} .finding-description {{ margin:0; color:#55635d; }}
    .source-block {{ margin-top:16px; overflow:hidden; border-radius:10px; color:#dbe9e3; background:var(--code); }} .source-location {{ padding:9px 13px; border-bottom:1px solid #345047; color:#91b9a9; font:11px ui-monospace,monospace; }} .source-block pre {{ margin:0; padding:13px; font:12px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace; }} .line-number {{ display:inline-block; min-width:28px; color:#6f9083; user-select:none; }}
    .fix {{ display:flex; gap:12px; margin-top:15px; padding:14px; border-radius:10px; color:#235642; background:#e1f0e9; }} .fix-icon {{ font-size:20px; }} .fix strong {{ font-size:12px; text-transform:uppercase; letter-spacing:.08em; }} .fix p {{ margin:3px 0 0; font-size:13px; }}
    .finding-footer {{ display:flex; justify-content:space-between; gap:16px; align-items:center; margin-top:15px; color:#7b8982; font-size:11px; }} .taxonomy {{ margin-right:5px; color:#52625a; background:#edf0eb; }} .filter-empty {{ padding:24px; border:1px dashed #b9c1ba; border-radius:12px; color:var(--muted); text-align:center; }}
    .section-divider {{ display:flex; align-items:center; gap:12px; margin:35px 0 0; color:var(--muted); font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.12em; }} .section-divider::after {{ content:""; height:1px; flex:1; background:var(--line); }}
    .steps {{ display:grid; gap:14px; margin-top:28px; }} .step {{ display:grid; grid-template-columns:56px 1fr; gap:18px; padding:24px; border:1px solid var(--line); border-radius:16px; background:var(--card); box-shadow:0 8px 30px rgba(30,48,40,.04); }}
    .step-number {{ color:var(--gold); font:800 15px/1 ui-monospace,monospace; padding-top:7px; }} .step h3 {{ margin:0 0 8px; font-size:20px; }} .step p {{ margin:5px 0; color:var(--muted); }}
    .command {{ margin:14px 0; padding:11px 14px; overflow:auto; border-radius:9px; color:#d7efe5; background:var(--code); font:13px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace; }} .command span {{ color:#65d6a8; }}
    pre {{ max-width:100%; overflow:auto; white-space:pre-wrap; overflow-wrap:anywhere; }} .evidence {{ max-height:360px; margin:12px 0 0; padding:16px; border-left:3px solid #63b995; border-radius:4px 10px 10px 4px; color:#d8e5df; background:#172a23; font:12px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace; }}
    .takeaways {{ margin-top:18px; padding:24px 28px; border-radius:16px; background:#e1eee8; }} .takeaways h3 {{ margin:0 0 10px; }} .takeaways ul {{ display:grid; grid-template-columns:1fr 1fr; gap:10px 24px; margin:0; padding:0; list-style:none; }}
    .takeaways li {{ display:flex; gap:10px; }} .check {{ color:var(--green); font-weight:900; }}
    details {{ margin-top:12px; border:1px solid var(--line); border-radius:12px; background:#eceee9; }} summary {{ cursor:pointer; padding:14px 18px; color:var(--muted); font-weight:700; }} details pre {{ max-height:540px; margin:0; padding:20px; border-top:1px solid var(--line); background:#f8f8f5; font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace; }}
    .report-meta {{ margin-top:28px; color:#9db7ac; font-size:13px; }}
    @media (max-width:800px) {{ .hero-grid,.layout {{ grid-template-columns:1fr; }} .hero-grid {{ gap:32px; }} nav {{ position:static; display:flex; max-height:none; overflow:auto; }} nav > small,.nav-report-link,.nav-finding-list {{ display:none; }} .nav-demo {{ min-width:max-content; border:0; }} .takeaways ul {{ grid-template-columns:1fr; }} .demo-heading,.finding-report-heading {{ display:block; }} .badges {{ justify-content:start; margin-top:14px; }} .finding-toolbar {{ display:block; }} .finding-controls {{ display:grid; justify-content:stretch; margin-top:12px; }} .finding-search,.finding-jump {{ display:grid; grid-template-columns:58px minmax(0,1fr); }} .finding-search input,.finding-jump select {{ width:100%; }} .finding-card h4 {{ font-size:18px; }} }}
    @media print {{ body {{ background:white; }} .hero {{ padding:36px; }} .layout {{ display:block; padding:30px; }} nav,details,.finding-toolbar {{ display:none; }} .demo {{ break-before:page; }} .step,.finding-card {{ break-inside:avoid; box-shadow:none; }} }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="brand"><span class="brand-mark">CG</span> CODEGUARD</div>
    <div class="hero-grid">
      <div><h1>Security checks that fit the way teams ship.</h1><p>A presentation-ready record of the CodeGuard showcase: local feedback, legacy adoption, CI integration, governed exceptions, and policy at scale.</p><div class="report-meta">Generated {esc(generated_label)}</div></div>
      <div class="scorecard"><div><strong>{len(results)}</strong><span>Showcases</span></div><div><strong>{active_findings}</strong><span>Active findings</span></div><div><strong>{high_risk}</strong><span>High risk</span></div><div><strong>{suppressed}</strong><span>Governed</span></div></div>
    </div>
  </header>
  <div class="layout"><nav><small>Report contents</small>{nav}</nav><main>{demos}</main></div>
  <script>
    document.querySelectorAll('.finding-report').forEach((report) => {{
      let activeFilter = 'all';
      let query = '';
      const cards = [...report.querySelectorAll('.finding-card')];
      const empty = report.querySelector('.filter-empty');
      const applyFilters = () => {{
        let visible = 0;
        cards.forEach((card) => {{
          const filterMatches = activeFilter === 'all' || card.dataset.severity === activeFilter || card.dataset.status === activeFilter;
          const searchMatches = !query || card.dataset.search.includes(query);
          card.hidden = !(filterMatches && searchMatches);
          if (!card.hidden) visible += 1;
        }});
        empty.hidden = visible !== 0;
      }};
      report.querySelectorAll('.filter-chip').forEach((button) => button.addEventListener('click', () => {{
        report.querySelectorAll('.filter-chip').forEach((item) => item.classList.remove('selected'));
        button.classList.add('selected');
        activeFilter = button.dataset.filter;
        applyFilters();
      }}));
      report.querySelector('.finding-search input').addEventListener('input', (event) => {{
        query = event.target.value.trim().toLowerCase();
        applyFilters();
      }});
      report.querySelector('.finding-jump select').addEventListener('change', (event) => {{
        if (event.target.value) window.location.hash = event.target.value;
      }});
    }});
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", nargs="?", default="all", choices=[*DEMOS, "all"])
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = list(DEMOS) if args.selection == "all" else [args.selection]
    results: list[DemoResult] = []
    for number in selected:
        print(f"Running Demo {number}: {DEMOS[number][0]}...", flush=True)
        results.append(run_demo(number))

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(results, datetime.now().astimezone()), encoding="utf-8")
    failed = [result.number for result in results if result.returncode != 0]
    print(f"HTML report created: {output}")
    if failed:
        print(f"Warning: demo(s) {', '.join(failed)} exited unexpectedly; details are in the report.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
