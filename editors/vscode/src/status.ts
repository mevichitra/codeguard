// SPDX-License-Identifier: Apache-2.0
import * as vscode from "vscode";
import { ClientState } from "./lsp";
import { SummaryCounts } from "./protocol";

const SCAN_TIMEOUT_MS = 5 * 60 * 1000;

/** Status-bar item: severity counts at a glance; click to open the Findings view. */
export class StatusIndicator implements vscode.Disposable {
  private readonly item = vscode.window.createStatusBarItem(
    "codeguard.status",
    vscode.StatusBarAlignment.Left,
    50
  );
  private counts: SummaryCounts | undefined;
  private state: ClientState = "stopped";
  private scanning = false;
  private scanWatchdog: NodeJS.Timeout | undefined;

  constructor() {
    this.item.name = "CodeGuard";
    this.item.command = "codeguard.focusFindings";
    this.render();
    this.item.show();
  }

  setState(state: ClientState): void {
    this.state = state;
    this.setScanning(state === "starting" || (this.scanning && state === "running"));
  }

  /**
   * The spinner is cleared when fresh counts arrive. A watchdog also clears it so a scan
   * that never reports back (failed summary request, unchanged results) cannot spin forever.
   */
  setScanning(scanning: boolean): void {
    if (this.scanWatchdog) {
      clearTimeout(this.scanWatchdog);
      this.scanWatchdog = undefined;
    }
    this.scanning = scanning;
    if (scanning) {
      this.scanWatchdog = setTimeout(() => this.setScanning(false), SCAN_TIMEOUT_MS);
    }
    this.render();
  }

  setCounts(counts: SummaryCounts): void {
    this.counts = counts;
    this.setScanning(false);
  }

  private render(): void {
    const item = this.item;
    item.backgroundColor = undefined;
    if (this.state === "missing") {
      item.text = "$(shield) CodeGuard: not installed";
      item.tooltip = "The codeguard executable was not found. Click for setup.";
      item.command = "codeguard.showSetup";
      item.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
      return;
    }
    item.command = "codeguard.focusFindings";
    if (this.state === "failed") {
      item.text = "$(shield) CodeGuard: error";
      item.tooltip = "The language server failed to start. Click to see the log.";
      item.command = "codeguard.showOutput";
      item.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
      return;
    }
    if (this.state === "stopped") {
      item.text = "$(shield) CodeGuard: off";
      item.tooltip = "CodeGuard is disabled (codeguard.enable).";
      return;
    }
    const c = this.counts;
    const spin = this.scanning ? "$(sync~spin) " : "";
    if (!c) {
      item.text = `${spin}$(shield) CodeGuard`;
      item.tooltip = "Scanning workspace…";
      return;
    }
    const blocking = c.bySeverity.critical + c.bySeverity.high;
    const warnings = c.bySeverity.medium;
    const notes = c.bySeverity.low + c.bySeverity.info;
    if (c.total === 0) {
      item.text = `${spin}$(shield) $(check)`;
    } else {
      item.text = `${spin}$(shield) $(error) ${blocking} $(warning) ${warnings} $(info) ${notes}`;
    }
    if (c.bySeverity.critical > 0) {
      item.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
    }
    const md = new vscode.MarkdownString(undefined, true);
    md.isTrusted = true;
    md.appendMarkdown(`**CodeGuard** — ${c.total} finding${c.total === 1 ? "" : "s"} in ${c.files} file${c.files === 1 ? "" : "s"}\n\n`);
    md.appendMarkdown(
      `| | |\n|---|---:|\n| Critical | ${c.bySeverity.critical} |\n| High | ${c.bySeverity.high} |\n` +
        `| Medium | ${c.bySeverity.medium} |\n| Low | ${c.bySeverity.low} |\n| Info | ${c.bySeverity.info} |\n\n`
    );
    const cats = Object.entries(c.byCategory)
      .map(([k, v]) => `${k} ${v}`)
      .join(" · ");
    if (cats) {
      md.appendMarkdown(`${cats}\n\n`);
    }
    if (c.fixable) {
      md.appendMarkdown(`$(wrench) ${c.fixable} fixable — [Fix all](command:codeguard.fixAllInWorkspace)\n\n`);
    }
    md.appendMarkdown("[Findings](command:codeguard.focusFindings) · [Security overview](command:codeguard.showOverview)");
    item.tooltip = md;
  }

  dispose(): void {
    if (this.scanWatchdog) {
      clearTimeout(this.scanWatchdog);
    }
    this.item.dispose();
  }
}
