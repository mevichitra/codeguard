#!/usr/bin/env python3
"""Render a self-contained HTML report from a CodeGuard JSON result."""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def source_excerpt(repository: Path, location: dict[str, Any]) -> tuple[str, str]:
    raw_path = Path(str(location.get("file", "")))
    path = raw_path if raw_path.is_absolute() else Path.cwd() / raw_path
    try:
        display = path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError:
        display = raw_path.as_posix()
    line_number = int(location.get("line", 1))
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return display, ""
    start = max(0, line_number - 2)
    end = min(len(lines), line_number + 1)
    excerpt = "\n".join(
        f"{number + 1:>4} | {lines[number]}" for number in range(start, end)
    )
    return display, excerpt


def render_finding(raw: dict[str, Any], repository: Path, index: int) -> str:
    severity = str(raw.get("severity", "info")).lower()
    location = raw.get("location", {})
    display_path, excerpt = source_excerpt(repository, location)
    status = "Suppressed" if raw.get("suppressed") else "Baselined" if raw.get("baselined") else "Active"
    status_key = status.lower()
    metadata = [raw.get("cwe"), raw.get("owasp"), raw.get("category")]
    metadata_html = "".join(f"<span>{esc(value)}</span>" for value in metadata if value)
    fix = raw.get("fix_suggestion")
    fix_html = f'<aside class="fix"><b>Recommended fix</b><p>{esc(fix)}</p></aside>' if fix else ""
    search = " ".join(
        str(raw.get(key, "")) for key in ("rule_id", "title", "description", "cwe", "owasp")
    ) + f" {display_path}"
    return f"""
      <article class="finding" id="finding-{index}" data-severity="{esc(severity)}" data-status="{status_key}" data-search="{esc(search.lower())}">
        <header>
          <div><span class="number">{index:02d}</span><code>{esc(raw.get('rule_id', 'UNKNOWN'))}</code></div>
          <div><span class="severity {esc(severity)}">{esc(severity.upper())}</span><span class="status">{status}</span></div>
        </header>
        <h3>{esc(raw.get('title', 'Untitled finding'))}</h3>
        <p class="description">{esc(raw.get('description', ''))}</p>
        <div class="location">{esc(display_path)}:{esc(location.get('line', 1))}:{esc(location.get('col', 1))}</div>
        {f'<pre>{esc(excerpt)}</pre>' if excerpt else ''}
        {fix_html}
        <footer><div>{metadata_html}</div><small>{round(float(raw.get('confidence', 0)) * 100)}% confidence</small></footer>
      </article>"""


def render(payload: dict[str, Any], repository: Path, commit: str) -> str:
    findings = sorted(
        payload.get("results", []),
        key=lambda item: (
            SEVERITY_ORDER.get(str(item.get("severity", "info")), 99),
            str(item.get("location", {}).get("file", "")),
            int(item.get("location", {}).get("line", 0)),
        ),
    )
    counts = Counter(str(item.get("severity", "info")).lower() for item in findings)
    active = sum(not item.get("suppressed") and not item.get("baselined") for item in findings)
    files = len({str(item.get("location", {}).get("file", "")) for item in findings})
    nav = "".join(
        f'<a href="#finding-{index}"><i class="{esc(str(item.get("severity", "info")))}"></i><span>{esc(item.get("rule_id", "UNKNOWN"))}</span><small>{esc(Path(str(item.get("location", {}).get("file", ""))).name)}:{esc(item.get("location", {}).get("line", 1))}</small></a>'
        for index, item in enumerate(findings, start=1)
    )
    cards = "".join(render_finding(item, repository, index) for index, item in enumerate(findings, start=1))
    filters = "".join(
        f'<button data-filter="{name}" class="{("selected" if name == "all" else "")}">{label}</button>'
        for name, label in [
            ("all", f"All {len(findings)}"),
            ("active", f"Active {active}"),
            ("critical", f"Critical {counts['critical']}"),
            ("high", f"High {counts['high']}"),
            ("medium", f"Medium {counts['medium']}"),
        ]
        if name in {"all", "active"} or counts[name]
    )
    generated = datetime.now().astimezone().strftime("%B %d, %Y at %I:%M %p %Z")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CodeGuard · OWASP NodeGoat Scan</title><style>
:root{{--ink:#15211d;--muted:#66756e;--paper:#f5f3ec;--card:#fffefa;--green:#0f6b4f;--mint:#dcefe6;--gold:#d99a2b;--line:#d9ddd6;--code:#12221c}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;color:var(--ink);background:var(--paper);font:15px/1.55 Inter,ui-sans-serif,system-ui,sans-serif}}
.hero{{padding:64px max(24px,calc((100vw - 1160px)/2));color:white;background:radial-gradient(circle at 85% 10%,#2b8b68 0,transparent 28%),linear-gradient(135deg,#10261e,#174d3b)}}
.brand{{font-weight:800;letter-spacing:.12em}}h1{{max-width:760px;margin:48px 0 16px;font-size:clamp(42px,7vw,72px);line-height:.98;letter-spacing:-.05em}}.hero p{{max-width:700px;color:#c8ddd4;font-size:18px}}
.meta{{margin-top:22px;color:#9db7ac;font:12px ui-monospace,monospace}}.summary{{display:grid;grid-template-columns:repeat(4,1fr);max-width:1160px;margin:-32px auto 48px;border:1px solid var(--line);border-radius:16px;background:white;box-shadow:0 12px 32px rgba(20,40,32,.08)}}
.summary div{{padding:22px;border-right:1px solid var(--line)}}.summary div:last-child{{border:0}}.summary strong{{display:block;font-size:28px}}.summary span{{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.1em}}
.layout{{display:grid;grid-template-columns:240px minmax(0,1fr);gap:44px;max-width:1160px;margin:auto;padding:0 24px 90px}}nav{{position:sticky;top:20px;max-height:calc(100vh - 40px);overflow:auto}}nav>span{{display:block;margin-bottom:10px;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.12em}}nav a{{display:grid;grid-template-columns:8px 90px 1fr;gap:7px;padding:6px 4px;color:var(--muted);text-decoration:none;font-size:11px}}nav a:hover{{color:var(--green)}}nav i{{width:7px;height:7px;margin-top:4px;border-radius:50%}}nav i.critical{{background:#9d1736}}nav i.high{{background:#d94b3d}}nav i.medium{{background:var(--gold)}}
.report-head{{display:flex;justify-content:space-between;gap:20px;align-items:end;padding-bottom:22px;border-bottom:1px solid var(--line)}}.eyebrow{{color:var(--green);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.13em}}h2{{margin:5px 0 0;font-size:34px;letter-spacing:-.03em}}.report-head p{{margin:8px 0 0;color:var(--muted)}}
.toolbar{{display:flex;justify-content:space-between;gap:14px;margin:22px 0}}.filters{{display:flex;flex-wrap:wrap;gap:7px}}button{{border:1px solid #c8cec8;border-radius:999px;padding:8px 12px;color:var(--muted);background:#f8f8f4;cursor:pointer;font-weight:750}}button.selected,button:hover{{border-color:var(--green);color:white;background:var(--green)}}input{{width:230px;border:1px solid #c8cec8;border-radius:9px;padding:9px 12px;background:white}}
.list{{display:grid;gap:14px}}.finding{{padding:23px;border:1px solid var(--line);border-radius:15px;background:var(--card);scroll-margin-top:20px;box-shadow:0 5px 20px rgba(30,48,40,.04)}}.finding[hidden]{{display:none}}.finding header,.finding footer{{display:flex;justify-content:space-between;gap:12px;align-items:center}}.finding header>div{{display:flex;align-items:center;gap:8px}}.number{{color:#93a099;font:700 12px ui-monospace,monospace}}.finding header code{{font-weight:800}}
.severity,.status,.finding footer span{{display:inline-block;border-radius:999px;padding:4px 8px;font-size:10px;font-weight:850;letter-spacing:.06em}}.severity{{color:white}}.severity.critical{{background:#9d1736}}.severity.high{{background:#d94b3d}}.severity.medium{{background:var(--gold)}}.status{{color:#526059;background:#e6e9e5}}h3{{margin:14px 0 6px;font-size:22px}}.description{{margin:0;color:#55635d}}.location{{margin-top:16px;padding:9px 13px;border-bottom:1px solid #345047;border-radius:10px 10px 0 0;color:#91b9a9;background:var(--code);font:11px ui-monospace,monospace}}
pre{{max-width:100%;margin:0;padding:14px;overflow:auto;white-space:pre-wrap;color:#dbe9e3;background:var(--code);font:12px/1.6 ui-monospace,monospace}}.fix{{margin-top:15px;padding:14px;border-radius:10px;color:#235642;background:#e1f0e9}}.fix b{{font-size:11px;text-transform:uppercase;letter-spacing:.08em}}.fix p{{margin:4px 0 0}}.finding footer{{margin-top:15px;color:#7b8982}}.finding footer span{{margin-right:5px;color:#52625a;background:#edf0eb}}.empty{{padding:24px;text-align:center;color:var(--muted)}}
@media(max-width:760px){{.summary{{grid-template-columns:1fr 1fr;margin:-20px 16px 36px}}.summary div:nth-child(2){{border-right:0}}.summary div:nth-child(-n+2){{border-bottom:1px solid var(--line)}}.layout{{grid-template-columns:1fr}}nav{{position:static;display:flex;overflow:auto}}nav>span{{display:none}}nav a{{min-width:max-content;grid-template-columns:8px auto}}nav a small{{display:none}}.toolbar{{display:block}}input{{width:100%;margin-top:12px}}}}
@media print{{nav,.toolbar{{display:none}}.hero{{padding:32px}}.summary{{margin:20px 0}}.layout{{display:block}}.finding{{break-inside:avoid;box-shadow:none}}}}
</style></head><body>
<header class="hero"><div class="brand">CODEGUARD / FIELD REPORT</div><h1>OWASP NodeGoat security scan</h1><p>A reproducible scan of a real-world intentionally vulnerable Node.js application, focused on first-party source code.</p><div class="meta">Repository: github.com/OWASP/NodeGoat · Revision: {esc(commit[:12])} · Generated {esc(generated)}</div></header>
<section class="summary"><div><strong>{len(findings)}</strong><span>Total findings</span></div><div><strong>{active}</strong><span>Active</span></div><div><strong>{counts['high'] + counts['critical']}</strong><span>High risk</span></div><div><strong>{files}</strong><span>Affected files</span></div></section>
<div class="layout"><nav><span>Finding index</span>{nav}</nav><main><div class="report-head"><div><span class="eyebrow">Real-world repository</span><h2>Individual findings</h2><p>Each result includes its source context and suggested remediation.</p></div></div><div class="toolbar"><div class="filters">{filters}</div><input type="search" placeholder="Search rule, file, or text…" aria-label="Search findings"></div><p class="empty" hidden>No findings match.</p><div class="list">{cards}</div></main></div>
<script>let filter='all',query='';const cards=[...document.querySelectorAll('.finding')],empty=document.querySelector('.empty');function apply(){{let shown=0;cards.forEach(card=>{{const match=(filter==='all'||card.dataset.severity===filter||card.dataset.status===filter)&&(!query||card.dataset.search.includes(query));card.hidden=!match;if(match)shown++}});empty.hidden=shown!==0}}document.querySelectorAll('button[data-filter]').forEach(button=>button.addEventListener('click',()=>{{document.querySelectorAll('button[data-filter]').forEach(item=>item.classList.remove('selected'));button.classList.add('selected');filter=button.dataset.filter;apply()}}));document.querySelector('input[type=search]').addEventListener('input',event=>{{query=event.target.value.toLowerCase().trim();apply()}})</script>
</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.write_text(render(payload, args.repository, args.commit), encoding="utf-8")
    print(f"HTML report written to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

