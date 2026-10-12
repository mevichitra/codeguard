// SPDX-License-Identifier: Apache-2.0
import * as path from "path";
import * as vscode from "vscode";
import { SEVERITIES, Severity, Summary, SummaryFile, SummaryFinding } from "./protocol";

export type Grouping = "severity" | "category" | "file";

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

const CATEGORY_LABEL: Record<string, string> = {
  security: "Security",
  performance: "Performance",
  quality: "Code quality",
  "ai-smell": "AI smells",
  meta: "Suppressions",
};
const CATEGORY_ICON: Record<string, string> = {
  security: "shield",
  performance: "dashboard",
  quality: "beaker",
  "ai-smell": "sparkle",
  meta: "comment-discussion",
};

export function severityIcon(severity: Severity): vscode.ThemeIcon {
  switch (severity) {
    case "critical":
      return new vscode.ThemeIcon("flame", new vscode.ThemeColor("problemsErrorIcon.foreground"));
    case "high":
      return new vscode.ThemeIcon("error", new vscode.ThemeColor("problemsErrorIcon.foreground"));
    case "medium":
      return new vscode.ThemeIcon("warning", new vscode.ThemeColor("problemsWarningIcon.foreground"));
    case "low":
      return new vscode.ThemeIcon("info", new vscode.ThemeColor("problemsInfoIcon.foreground"));
    default:
      return new vscode.ThemeIcon("lightbulb");
  }
}

interface Entry {
  file: SummaryFile;
  finding: SummaryFinding;
}

export type Node =
  | { kind: "group"; key: string; label: string; icon: vscode.ThemeIcon; entries: Entry[] }
  | { kind: "file"; file: SummaryFile; entries: Entry[]; parentKey: string }
  | { kind: "finding"; file: SummaryFile; finding: SummaryFinding };

/** Arguments of the codeguard.revealFinding command (also used by context-menu commands). */
export interface FindingRef {
  uri: string;
  finding: SummaryFinding;
}

export class FindingsProvider implements vscode.TreeDataProvider<Node> {
  private readonly changeEmitter = new vscode.EventEmitter<Node | undefined>();
  readonly onDidChangeTreeData = this.changeEmitter.event;

  private summary: Summary | undefined;
  private grouping: Grouping;
  private severities: Set<Severity>;

  constructor(private readonly memento: vscode.Memento) {
    this.grouping = memento.get<Grouping>("codeguard.grouping", "severity");
    this.severities = new Set(memento.get<Severity[]>("codeguard.severities", SEVERITIES));
  }

  get currentGrouping(): Grouping {
    return this.grouping;
  }

  get visibleSeverities(): Severity[] {
    return SEVERITIES.filter((s) => this.severities.has(s));
  }

  get data(): Summary | undefined {
    return this.summary;
  }

  update(summary: Summary | undefined): void {
    this.summary = summary;
    this.changeEmitter.fire(undefined);
  }

  setGrouping(grouping: Grouping): void {
    this.grouping = grouping;
    void this.memento.update("codeguard.grouping", grouping);
    this.changeEmitter.fire(undefined);
  }

  setSeverities(severities: Severity[]): void {
    this.severities = new Set(severities);
    void this.memento.update("codeguard.severities", severities);
    this.changeEmitter.fire(undefined);
  }

  /** Total and visible finding counts, for the view badge and message. */
  stats(): { total: number; visible: number } {
    const total = this.summary?.counts.total ?? 0;
    return { total, visible: this.entries().length };
  }

  private entries(): Entry[] {
    const out: Entry[] = [];
    for (const file of this.summary?.files ?? []) {
      for (const finding of file.findings) {
        if (this.severities.has(finding.severity)) {
          out.push({ file, finding });
        }
      }
    }
    return out;
  }

  getChildren(node?: Node): Node[] {
    if (!node) {
      const entries = this.entries();
      if (this.grouping === "file") {
        return byFile(entries, "root");
      }
      return this.grouping === "severity" ? bySeverity(entries) : byCategory(entries);
    }
    if (node.kind === "group") {
      return byFile(node.entries, node.key);
    }
    if (node.kind === "file") {
      return node.entries.map((e) => ({ kind: "finding", file: e.file, finding: e.finding }));
    }
    return [];
  }

  getTreeItem(node: Node): vscode.TreeItem {
    if (node.kind === "group") {
      const item = new vscode.TreeItem(node.label, vscode.TreeItemCollapsibleState.Expanded);
      item.id = `group:${node.key}`;
      item.iconPath = node.icon;
      item.description = String(node.entries.length);
      item.contextValue = "group";
      return item;
    }
    if (node.kind === "file") {
      const uri = vscode.Uri.parse(node.file.uri);
      const collapsed =
        this.grouping === "file"
          ? vscode.TreeItemCollapsibleState.Expanded
          : vscode.TreeItemCollapsibleState.Collapsed;
      const item = new vscode.TreeItem(uri, collapsed);
      item.id = `file:${node.parentKey}:${node.file.uri}`;
      item.iconPath = vscode.ThemeIcon.File;
      const dir = path.posix.dirname(node.file.path);
      item.description = `${dir === "." ? "" : dir + " · "}${node.entries.length}`;
      item.contextValue = "file";
      return item;
    }
    const f = node.finding;
    const item = new vscode.TreeItem(f.title, vscode.TreeItemCollapsibleState.None);
    item.id = `finding:${node.file.uri}:${f.fingerprint}:${f.line}:${f.col}:${f.ruleId}`;
    item.iconPath = severityIcon(f.severity);
    item.description = `${f.ruleId} · Ln ${f.line}${f.hasFix ? " · fixable" : ""}`;
    item.contextValue = f.hasFix ? "finding.fixable" : "finding";
    item.tooltip = findingTooltip(f, node.file.path);
    const ref: FindingRef = { uri: node.file.uri, finding: f };
    item.command = { title: "Reveal", command: "codeguard.revealFinding", arguments: [ref] };
    return item;
  }

  dispose(): void {
    this.changeEmitter.dispose();
  }
}

function bySeverity(entries: Entry[]): Node[] {
  const out: Node[] = [];
  for (const severity of SEVERITIES) {
    const group = entries.filter((e) => e.finding.severity === severity);
    if (group.length) {
      out.push({
        kind: "group",
        key: `severity:${severity}`,
        label: SEVERITY_LABEL[severity],
        icon: severityIcon(severity),
        entries: group,
      });
    }
  }
  return out;
}

function byCategory(entries: Entry[]): Node[] {
  const categories = Array.from(new Set(entries.map((e) => e.finding.category))).sort((a, b) =>
    a === "security" ? -1 : b === "security" ? 1 : a.localeCompare(b)
  );
  return categories.map((category) => ({
    kind: "group" as const,
    key: `category:${category}`,
    label: CATEGORY_LABEL[category] ?? category,
    icon: new vscode.ThemeIcon(CATEGORY_ICON[category] ?? "circle-outline"),
    entries: entries.filter((e) => e.finding.category === category),
  }));
}

function byFile(entries: Entry[], parentKey: string): Node[] {
  const files = new Map<string, Entry[]>();
  for (const e of entries) {
    const list = files.get(e.file.uri) ?? [];
    list.push(e);
    files.set(e.file.uri, list);
  }
  return Array.from(files.values())
    .sort((a, b) => worst(a) - worst(b) || a[0].file.path.localeCompare(b[0].file.path))
    .map((list) => ({ kind: "file" as const, file: list[0].file, entries: list, parentKey }));
}

function worst(entries: Entry[]): number {
  return Math.min(...entries.map((e) => SEVERITIES.indexOf(e.finding.severity)));
}

function findingTooltip(f: SummaryFinding, filePath: string): vscode.MarkdownString {
  const md = new vscode.MarkdownString(undefined, true);
  md.appendMarkdown(`**${escapeMd(f.title)}**\n\n`);
  md.appendMarkdown(
    `\`${f.severity.toUpperCase()}\` · ${f.category} · \`${f.ruleId}\`${f.cwe ? ` · ${f.cwe}` : ""}\n\n`
  );
  md.appendMarkdown(`${escapeMd(f.description)}\n\n`);
  md.appendMarkdown(`${escapeMd(filePath)}:${f.line}:${f.col}`);
  if (f.hasFix) {
    md.appendMarkdown("\n\n$(wrench) A safe quick fix is available.");
  }
  return md;
}

function escapeMd(text: string): string {
  return text.replace(/[\\`*_{}[\]<>#|]/g, (c) => `\\${c}`);
}
