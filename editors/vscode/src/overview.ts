// SPDX-License-Identifier: Apache-2.0
import * as crypto from "crypto";
import * as vscode from "vscode";
import { SEVERITIES, Severity, Summary } from "./protocol";

type Message =
  | { type: "open"; uri: string; line: number; col: number }
  | { type: "fixAll" }
  | { type: "rescan" }
  | { type: "focusFindings" }
  | { type: "explain"; ruleId: string };

/** A single "Security Overview" webview: totals, severity bars, top rules and files. */
export class OverviewPanel implements vscode.Disposable {
  private static current: OverviewPanel | undefined;
  private readonly disposables: vscode.Disposable[] = [];

  static show(summary: Summary | undefined, extensionUri: vscode.Uri): OverviewPanel {
    if (OverviewPanel.current) {
      OverviewPanel.current.panel.reveal(vscode.ViewColumn.Active);
      OverviewPanel.current.update(summary);
      return OverviewPanel.current;
    }
    const panel = vscode.window.createWebviewPanel(
      "codeguard.overview",
      "CodeGuard Overview",
      vscode.ViewColumn.Active,
      { enableScripts: true, retainContextWhenHidden: false, localResourceRoots: [] }
    );
    panel.iconPath = vscode.Uri.joinPath(extensionUri, "media", "shield.svg");
    OverviewPanel.current = new OverviewPanel(panel);
    OverviewPanel.current.update(summary);
    return OverviewPanel.current;
  }

  /** Refresh the open panel, if any. */
  static refresh(summary: Summary | undefined): void {
    OverviewPanel.current?.update(summary);
  }

  private constructor(private readonly panel: vscode.WebviewPanel) {
    panel.onDidDispose(() => this.dispose(), null, this.disposables);
    panel.webview.onDidReceiveMessage((m: Message) => this.onMessage(m), null, this.disposables);
  }

  private async onMessage(message: Message): Promise<void> {
    switch (message.type) {
      case "open": {
        const doc = await vscode.workspace.openTextDocument(vscode.Uri.parse(message.uri));
        const pos = new vscode.Position(Math.max(message.line - 1, 0), Math.max(message.col - 1, 0));
        await vscode.window.showTextDocument(doc, {
          selection: new vscode.Range(pos, pos),
          viewColumn: vscode.ViewColumn.Beside,
        });
        break;
      }
      case "fixAll":
        await vscode.commands.executeCommand("codeguard.fixAllInWorkspace");
        break;
      case "rescan":
        await vscode.commands.executeCommand("codeguard.scanWorkspace");
        break;
      case "focusFindings":
        await vscode.commands.executeCommand("codeguard.focusFindings");
        break;
      case "explain":
        await vscode.commands.executeCommand("codeguard.explain", message.ruleId);
        break;
    }
  }

  update(summary: Summary | undefined): void {
    this.panel.webview.html = renderOverview(summary, this.panel.webview.cspSource);
  }

  dispose(): void {
    OverviewPanel.current = undefined;
    this.panel.dispose();
    while (this.disposables.length) {
      this.disposables.pop()?.dispose();
    }
  }
}

const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "var(--vscode-errorForeground)",
  high: "var(--vscode-editorError-foreground, var(--vscode-errorForeground))",
  medium: "var(--vscode-editorWarning-foreground)",
  low: "var(--vscode-editorInfo-foreground)",
  info: "var(--vscode-descriptionForeground)",
};

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Pure HTML rendering (exported for tests and reuse). */
export function renderOverview(summary: Summary | undefined, cspSource: string): string {
  const nonce = crypto.randomBytes(16).toString("base64");
  const body = summary ? renderBody(summary) : `<p class="muted">Waiting for the first scan…</p>`;
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${cspSource} 'nonce-${nonce}'; script-src 'nonce-${nonce}';">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeGuard Overview</title>
<style nonce="${nonce}">
  body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); padding: 16px 24px; max-width: 980px; }
  h1 { font-size: 1.4em; font-weight: 600; margin: 0 0 4px; }
  h2 { font-size: 1.05em; font-weight: 600; margin: 24px 0 8px; }
  .muted { color: var(--vscode-descriptionForeground); }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin-top: 16px; }
  .tile { border: 1px solid var(--vscode-panel-border, transparent); background: var(--vscode-editorWidget-background); border-radius: 6px; padding: 12px; }
  .tile .n { font-size: 1.8em; font-weight: 600; font-variant-numeric: tabular-nums; }
  .bar { display: grid; grid-template-columns: 80px 1fr 40px; align-items: center; gap: 8px; margin: 4px 0; }
  .track { background: var(--vscode-editorWidget-background); border-radius: 3px; height: 10px; overflow: hidden; }
  .fill { height: 100%; border-radius: 3px; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  table { border-collapse: collapse; width: 100%; }
  td, th { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--vscode-panel-border, rgba(128,128,128,.2)); }
  th { font-weight: 600; color: var(--vscode-descriptionForeground); }
  a, .link { color: var(--vscode-textLink-foreground); cursor: pointer; text-decoration: none; }
  a:hover, .link:hover { text-decoration: underline; }
  button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 6px 12px; border-radius: 2px; cursor: pointer; margin-right: 8px; }
  button.secondary { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); }
  button:hover { background: var(--vscode-button-hoverBackground); }
  .actions { margin-top: 16px; }
  .pill { display: inline-block; padding: 0 6px; border-radius: 8px; font-size: .85em; border: 1px solid currentColor; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  @media (max-width: 700px) { .cols { grid-template-columns: 1fr; } }
</style>
</head>
<body>
${body}
<script nonce="${nonce}">
  const vscode = acquireVsCodeApi();
  document.addEventListener("click", (event) => {
    const el = event.target.closest("[data-action]");
    if (!el) return;
    const action = el.dataset.action;
    if (action === "open") {
      vscode.postMessage({ type: "open", uri: el.dataset.uri, line: Number(el.dataset.line), col: Number(el.dataset.col) });
    } else if (action === "explain") {
      vscode.postMessage({ type: "explain", ruleId: el.dataset.rule });
    } else {
      vscode.postMessage({ type: action });
    }
  });
</script>
</body>
</html>`;
}

function renderBody(s: Summary): string {
  const c = s.counts;
  const max = Math.max(1, ...SEVERITIES.map((sev) => c.bySeverity[sev]));
  const bars = SEVERITIES.map((sev) => {
    const n = c.bySeverity[sev];
    const width = Math.round((n / max) * 100);
    return `<div class="bar"><span>${sev[0].toUpperCase() + sev.slice(1)}</span><div class="track"><div class="fill" style="width:${width}%;background:${SEVERITY_COLOR[sev]}"></div></div><span class="num">${n}</span></div>`;
  }).join("");
  const categories = Object.entries(c.byCategory)
    .map(([k, v]) => `<div class="tile"><div class="n">${v}</div><div class="muted">${escapeHtml(k)}</div></div>`)
    .join("");
  const rules = s.rules
    .slice(0, 8)
    .map(
      (r) =>
        `<tr><td><span class="link" data-action="explain" data-rule="${escapeHtml(r.id)}">${escapeHtml(r.id)}</span></td><td>${escapeHtml(r.title)}${r.hasFix ? ' <span class="pill">fix</span>' : ""}</td><td class="num">${r.count}</td></tr>`
    )
    .join("");
  const files = [...s.files]
    .sort((a, b) => b.counts.total - a.counts.total)
    .slice(0, 8)
    .map((f) => {
      const first = f.findings[0];
      return `<tr><td><span class="link" data-action="open" data-uri="${escapeHtml(f.uri)}" data-line="${first?.line ?? 1}" data-col="${first?.col ?? 1}">${escapeHtml(f.path)}</span></td><td class="num">${f.counts.total}</td></tr>`;
    })
    .join("");
  const generated = new Date(s.generatedAt).toLocaleString();
  const empty = c.total === 0
    ? `<p>✅ No active findings. Suppressed: ${c.suppressed}, baselined: ${c.baselined}.</p>`
    : "";
  return `
<h1>🛡 CodeGuard Overview</h1>
<div class="muted">${escapeHtml(s.workspaceRoot)} · updated ${escapeHtml(generated)} · analysis ran locally</div>
<div class="tiles">
  <div class="tile"><div class="n">${c.total}</div><div class="muted">active findings</div></div>
  <div class="tile"><div class="n">${c.bySeverity.critical + c.bySeverity.high}</div><div class="muted">critical + high</div></div>
  <div class="tile"><div class="n">${c.fixable}</div><div class="muted">safe autofixes</div></div>
  <div class="tile"><div class="n">${c.files}</div><div class="muted">files affected</div></div>
</div>
<div class="actions">
  ${c.fixable ? `<button data-action="fixAll">Fix ${c.fixable} safe issue${c.fixable === 1 ? "" : "s"}</button>` : ""}
  <button class="secondary" data-action="focusFindings">Open Findings view</button>
  <button class="secondary" data-action="rescan">Rescan workspace</button>
</div>
${empty}
<h2>By severity</h2>
${bars}
${categories ? `<h2>By category</h2><div class="tiles">${categories}</div>` : ""}
<div class="cols">
  <div><h2>Top rules</h2><table><tr><th>Rule</th><th>Title</th><th class="num">Count</th></tr>${rules || '<tr><td colspan="3" class="muted">None</td></tr>'}</table></div>
  <div><h2>Top files</h2><table><tr><th>File</th><th class="num">Findings</th></tr>${files || '<tr><td colspan="2" class="muted">None</td></tr>'}</table></div>
</div>
<p class="muted" style="margin-top:24px">Suppressed: ${c.suppressed} · Baselined: ${c.baselined}</p>`;
}
