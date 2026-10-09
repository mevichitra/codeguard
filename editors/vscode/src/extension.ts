// SPDX-License-Identifier: Apache-2.0
import { execFile } from "child_process";
import * as vscode from "vscode";
import { FindingRef, FindingsProvider, Grouping, Node } from "./findingsView";
import { findCodeGuardExecutable, getEnhancedEnv } from "./locate";
import { CodeGuardClient, SEVERITIES, ServerCommand, Severity, Summary } from "./lsp";
import { OverviewPanel } from "./overview";
import { StatusIndicator } from "./status";
import { byteColumnToCharacter } from "./text";

const INSTALL_COMMAND = "pipx install codeguard-cli";
const SETTINGS_FOR_SERVER = [
  "codeguard.severity.map",
  "codeguard.categories",
  "codeguard.rules.disable",
  "codeguard.scanWorkspaceOnStartup",
];

let client: CodeGuardClient | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const lsp = new CodeGuardClient();
  client = lsp;
  const status = new StatusIndicator();
  const provider = new FindingsProvider(context.workspaceState);
  const treeView = vscode.window.createTreeView("codeguard.findings", {
    treeDataProvider: provider,
    showCollapseAll: true,
  });
  context.subscriptions.push(lsp, status, provider, treeView);

  // ---------------------------------------------------------------------
  // Keep the tree, status bar, and overview in sync with the server
  // ---------------------------------------------------------------------

  let refreshTimer: NodeJS.Timeout | undefined;
  const refresh = (): void => {
    if (refreshTimer) {
      clearTimeout(refreshTimer);
    }
    refreshTimer = setTimeout(async () => {
      let summary: Summary | undefined;
      try {
        summary = await lsp.summary();
      } catch {
        summary = undefined;
      }
      provider.update(summary);
      if (summary) {
        status.setCounts(summary.counts);
      }
      OverviewPanel.refresh(summary);
      updateViewChrome(treeView, provider);
    }, 100);
  };
  context.subscriptions.push(
    { dispose: () => refreshTimer && clearTimeout(refreshTimer) },
    lsp.onDidChangeSummary(() => refresh()),
    lsp.onDidChangeState((state) => {
      status.setState(state);
      if (state === "running") {
        refresh();
      } else if (state === "missing") {
        provider.update(undefined);
        void promptInstall();
      }
    })
  );

  // ---------------------------------------------------------------------
  // Commands
  // ---------------------------------------------------------------------

  const register = (id: string, fn: (...args: any[]) => unknown): void => {
    context.subscriptions.push(vscode.commands.registerCommand(id, fn));
  };

  register("codeguard.focusFindings", () =>
    vscode.commands.executeCommand("codeguard.findings.focus")
  );

  register("codeguard.showOverview", async () => {
    OverviewPanel.show(provider.data ?? (await lsp.summary().catch(() => undefined)), context.extensionUri);
  });

  register("codeguard.scanWorkspace", async () => {
    if (!(await ensureRunning(lsp))) {
      return;
    }
    status.setScanning(true);
    await lsp.executeServerCommand(ServerCommand.scanWorkspace);
  });

  register("codeguard.openDashboard", async () => {
    if (!(await ensureRunning(lsp))) {
      return;
    }
    await lsp.executeServerCommand(ServerCommand.openDashboard);
  });

  register("codeguard.restartServer", async () => {
    await lsp.restart();
    if (lsp.isRunning()) {
      void vscode.window.showInformationMessage("CodeGuard language server restarted.");
    }
  });

  register("codeguard.showOutput", () => lsp.showOutput());
  register("codeguard.showSetup", () => promptInstall(true));

  register("codeguard.fixAllInFile", async (uri?: vscode.Uri) => {
    const target = uri instanceof vscode.Uri ? uri : vscode.window.activeTextEditor?.document.uri;
    if (!target || !(await ensureRunning(lsp))) {
      return;
    }
    const count = await lsp.fixAll(target);
    void vscode.window.showInformationMessage(
      count ? `CodeGuard applied ${count} safe fix${count === 1 ? "" : "es"}.` : "No safe fixes in this file."
    );
  });

  register("codeguard.fixAllInWorkspace", async () => {
    if (!(await ensureRunning(lsp))) {
      return;
    }
    const fixable = provider.data?.counts.fixable ?? 0;
    if (!fixable) {
      void vscode.window.showInformationMessage("CodeGuard found no safe fixes in the workspace.");
      return;
    }
    const choice = await vscode.window.showWarningMessage(
      `Apply ${fixable} safe CodeGuard fix${fixable === 1 ? "" : "es"} across the workspace?`,
      { modal: true, detail: "Edited files are left unsaved so you can review them first." },
      "Apply Fixes"
    );
    if (choice !== "Apply Fixes") {
      return;
    }
    const count = await lsp.fixAll();
    void vscode.window.showInformationMessage(
      `CodeGuard applied ${count} safe fix${count === 1 ? "" : "es"}. Review and save the edited files.`
    );
  });

  register("codeguard.revealFinding", async (arg: FindingRef | Node) => {
    const ref = toRef(arg);
    if (!ref) {
      return;
    }
    const doc = await vscode.workspace.openTextDocument(vscode.Uri.parse(ref.uri));
    const range = findingRange(doc, ref);
    await vscode.window.showTextDocument(doc, { selection: range, preserveFocus: false });
  });

  register("codeguard.fixFinding", async (arg: FindingRef | Node) => {
    const ref = toRef(arg);
    if (ref) {
      await applyServerAction(ref, (title) => title.startsWith("Fix:"));
    }
  });

  register("codeguard.suppressFinding", async (arg: FindingRef | Node) => {
    const ref = toRef(arg);
    if (ref) {
      await applyServerAction(ref, (title) => title === `Suppress ${ref.finding.ruleId} on this line`);
    }
  });

  register("codeguard.explain", async (arg?: string | FindingRef | Node) => {
    const ref = typeof arg === "string" ? undefined : toRef(arg);
    const ruleId = typeof arg === "string" ? arg : ref?.finding.ruleId;
    if (!ruleId) {
      return;
    }
    const uri =
      ref?.finding.helpUri ?? `https://mevichitra.github.io/codeguard/rules/${encodeURIComponent(ruleId)}/`;
    await vscode.env.openExternal(vscode.Uri.parse(uri));
  });

  register("codeguard.copyFingerprint", async (arg: FindingRef | Node) => {
    const ref = toRef(arg);
    if (ref?.finding.fingerprint) {
      await vscode.env.clipboard.writeText(ref.finding.fingerprint);
      void vscode.window.setStatusBarMessage("CodeGuard fingerprint copied", 2000);
    }
  });

  register("codeguard.setGrouping", async () => {
    const options: { label: string; value: Grouping }[] = [
      { label: "$(warning) Severity", value: "severity" },
      { label: "$(symbol-class) Category", value: "category" },
      { label: "$(file) File", value: "file" },
    ];
    const pick = await vscode.window.showQuickPick(
      options.map((o) => ({ ...o, picked: o.value === provider.currentGrouping })),
      { title: "Group CodeGuard findings by" }
    );
    if (pick) {
      provider.setGrouping(pick.value);
    }
  });

  register("codeguard.filterSeverity", async () => {
    const visible = new Set(provider.visibleSeverities);
    const picks = await vscode.window.showQuickPick(
      SEVERITIES.map((s) => ({ label: s[0].toUpperCase() + s.slice(1), value: s, picked: visible.has(s) })),
      { canPickMany: true, title: "Show findings with severity" }
    );
    if (picks) {
      provider.setSeverities(picks.map((p) => p.value as Severity));
      updateViewChrome(treeView, provider);
    }
  });

  register("codeguard.exportSarif", async () => {
    const folder = vscode.workspace.workspaceFolders?.[0];
    const executable = findCodeGuardExecutable(vscode.workspace.workspaceFolders);
    if (!folder || !executable) {
      void vscode.window.showErrorMessage("CodeGuard: open a folder and install codeguard first.");
      return;
    }
    const configured = vscode.workspace.getConfiguration("codeguard").get<string>("sarif.outputPath", "");
    const target = await vscode.window.showSaveDialog({
      defaultUri: vscode.Uri.joinPath(folder.uri, configured || "codeguard.sarif"),
      filters: { SARIF: ["sarif", "json"] },
      title: "Export CodeGuard SARIF report",
    });
    if (!target) {
      return;
    }
    await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: "CodeGuard: exporting SARIF…" },
      () =>
        new Promise<void>((resolve) => {
          execFile(
            executable,
            ["scan", folder.uri.fsPath, "--format", "sarif", "-o", target.fsPath, "--exit-zero", "-q"],
            { cwd: folder.uri.fsPath, env: getEnhancedEnv(vscode.workspace.workspaceFolders) },
            async (error, _stdout, stderr) => {
              if (error) {
                void vscode.window.showErrorMessage(`CodeGuard SARIF export failed: ${stderr || error.message}`);
              } else {
                const open = await vscode.window.showInformationMessage(
                  `SARIF report written to ${vscode.workspace.asRelativePath(target)}.`,
                  "Open"
                );
                if (open) {
                  await vscode.window.showTextDocument(target);
                }
              }
              resolve();
            }
          );
        })
    );
  });

  register("codeguard.openSample", async () => {
    const source = vscode.Uri.joinPath(context.extensionUri, "media", "sample", "vulnerable.py");
    const target = vscode.Uri.joinPath(context.globalStorageUri, "sample", "codeguard_sample.py");
    await vscode.workspace.fs.createDirectory(vscode.Uri.joinPath(context.globalStorageUri, "sample"));
    await vscode.workspace.fs.copy(source, target, { overwrite: true });
    await vscode.window.showTextDocument(target);
  });

  // ---------------------------------------------------------------------
  // Settings
  // ---------------------------------------------------------------------

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(async (event) => {
      if (event.affectsConfiguration("codeguard.enable") || event.affectsConfiguration("codeguard.path")) {
        await lsp.restart();
      } else if (SETTINGS_FOR_SERVER.some((key) => event.affectsConfiguration(key))) {
        status.setScanning(true);
        await lsp.sendSettings();
      }
    })
  );

  await lsp.start();
}

export async function deactivate(): Promise<void> {
  await client?.stop();
  client = undefined;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toRef(arg: unknown): FindingRef | undefined {
  if (!arg || typeof arg !== "object") {
    return undefined;
  }
  const node = arg as Partial<Node> & Partial<FindingRef>;
  if (node.kind === "finding" && "file" in node && node.file && "finding" in node && node.finding) {
    return { uri: node.file.uri, finding: node.finding };
  }
  if (typeof node.uri === "string" && node.finding) {
    return { uri: node.uri, finding: node.finding };
  }
  return undefined;
}

function findingRange(doc: vscode.TextDocument, ref: FindingRef): vscode.Range {
  // Summary columns are UTF-8 byte offsets; map them onto the document's characters.
  const f = ref.finding;
  const start = bytePosition(doc, f.line, f.col);
  const end = f.endLine && f.endCol ? bytePosition(doc, f.endLine, f.endCol) : start;
  return new vscode.Range(start, end);
}

function bytePosition(doc: vscode.TextDocument, line: number, byteCol: number): vscode.Position {
  const index = Math.min(Math.max(line - 1, 0), Math.max(doc.lineCount - 1, 0));
  const text = doc.lineAt(index).text;
  return new vscode.Position(index, Math.min(byteColumnToCharacter(text, byteCol), text.length));
}

async function applyServerAction(ref: FindingRef, match: (title: string) => boolean): Promise<void> {
  const uri = vscode.Uri.parse(ref.uri);
  const doc = await vscode.workspace.openTextDocument(uri);
  const range = findingRange(doc, ref);
  const actions = await vscode.commands.executeCommand<vscode.CodeAction[]>(
    "vscode.executeCodeActionProvider",
    uri,
    range,
    vscode.CodeActionKind.QuickFix.value
  );
  const action = (actions ?? []).find(
    (a) => a.title.includes(ref.finding.ruleId) && match(a.title) && a.edit
  );
  if (!action?.edit) {
    void vscode.window.showInformationMessage(`No matching action for ${ref.finding.ruleId}.`);
    return;
  }
  await vscode.workspace.applyEdit(action.edit);
  await vscode.window.showTextDocument(doc, { selection: range });
}

async function ensureRunning(lsp: CodeGuardClient): Promise<boolean> {
  if (lsp.isRunning()) {
    return true;
  }
  if (lsp.state === "missing") {
    await promptInstall(true);
    return false;
  }
  void vscode.window.showWarningMessage(
    "The CodeGuard language server is not running. Check the CodeGuard output or restart it."
  );
  return false;
}

let installPromptShown = false;

async function promptInstall(force = false): Promise<void> {
  if (installPromptShown && !force) {
    return;
  }
  installPromptShown = true;
  const copy = "Copy Install Command";
  const settings = "Set Path…";
  const guide = "Getting Started";
  const choice = await vscode.window.showWarningMessage(
    `CodeGuard was not found on PATH or in a workspace virtual environment. Install it with \`${INSTALL_COMMAND}\` (or \`uv tool install codeguard-cli\`), or set \`codeguard.path\`.`,
    copy,
    settings,
    guide
  );
  if (choice === copy) {
    await vscode.env.clipboard.writeText(INSTALL_COMMAND);
    void vscode.window.showInformationMessage(`Copied \`${INSTALL_COMMAND}\`. Run it, then CodeGuard: Restart Server.`);
  } else if (choice === settings) {
    await vscode.commands.executeCommand("workbench.action.openSettings", "codeguard.path");
  } else if (choice === guide) {
    await vscode.commands.executeCommand(
      "workbench.action.openWalkthrough",
      "codeguard.codeguard#gettingStarted",
      false
    );
  }
}

function updateViewChrome(view: vscode.TreeView<Node>, provider: FindingsProvider): void {
  const { total, visible } = provider.stats();
  view.badge = total ? { value: total, tooltip: `${total} CodeGuard finding${total === 1 ? "" : "s"}` } : undefined;
  const filtered = provider.visibleSeverities.length < SEVERITIES.length;
  view.message = filtered ? `Showing ${visible} of ${total} (filtered by severity)` : undefined;
  view.description = provider.currentGrouping === "severity" ? undefined : `by ${provider.currentGrouping}`;
}
