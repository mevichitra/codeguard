// SPDX-License-Identifier: Apache-2.0
import * as vscode from "vscode";
import {
  DocumentSelector,
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  State,
  WorkspaceEdit as LspWorkspaceEdit,
} from "vscode-languageclient/node";
import { findCodeGuardExecutable, getEnhancedEnv } from "./locate";

import { Summary, SummaryCounts } from "./protocol";

export * from "./protocol";

/** Commands the language server executes (namespaced to avoid clashing with ours). */
export const ServerCommand = {
  openDashboard: "codeguard.lsp.openDashboard",
  explain: "codeguard.lsp.explain",
  scanWorkspace: "codeguard.lsp.scanWorkspace",
  fixAll: "codeguard.lsp.fixAll",
} as const;

export type ClientState = "stopped" | "starting" | "running" | "missing" | "failed";

/** Editor settings in the shape the server reads (initializationOptions / didChangeConfiguration). */
export function buildServerSettings(): Record<string, unknown> {
  const config = vscode.workspace.getConfiguration("codeguard");
  return {
    client: "vscode",
    codeDescription: "help",
    severityMap: config.get<Record<string, string>>("severity.map", {}),
    categories: config.get<Record<string, boolean>>("categories", {}),
    rules: { disable: config.get<string[]>("rules.disable", []) },
    scanWorkspaceOnStartup: config.get<boolean>("scanWorkspaceOnStartup", true),
  };
}

const DOCUMENT_SELECTOR: DocumentSelector = [
  { scheme: "file", language: "python" },
  { scheme: "file", language: "javascript" },
  { scheme: "file", language: "javascriptreact" },
  { scheme: "file", language: "typescript" },
  { scheme: "file", language: "typescriptreact" },
];

/** Owns the LanguageClient and exposes CodeGuard's custom protocol as typed calls. */
export class CodeGuardClient implements vscode.Disposable {
  private client: LanguageClient | undefined;
  private readonly summaryEmitter = new vscode.EventEmitter<SummaryCounts>();
  private readonly stateEmitter = new vscode.EventEmitter<ClientState>();
  private currentState: ClientState = "stopped";
  private readonly output = vscode.window.createOutputChannel("CodeGuard");

  /** Fires (debounced by the server) whenever findings change anywhere in the workspace. */
  readonly onDidChangeSummary = this.summaryEmitter.event;
  readonly onDidChangeState = this.stateEmitter.event;

  get state(): ClientState {
    return this.currentState;
  }

  private setState(state: ClientState): void {
    this.currentState = state;
    void vscode.commands.executeCommand("setContext", "codeguard.state", state);
    this.stateEmitter.fire(state);
  }

  isRunning(): boolean {
    return this.client?.state === State.Running;
  }

  async start(): Promise<void> {
    const config = vscode.workspace.getConfiguration("codeguard");
    if (!config.get<boolean>("enable", true)) {
      this.setState("stopped");
      return;
    }
    const folders = vscode.workspace.workspaceFolders;
    const command = findCodeGuardExecutable(folders);
    if (!command) {
      this.setState("missing");
      return;
    }
    this.setState("starting");
    const serverOptions: ServerOptions = {
      command,
      args: ["lsp"],
      options: { cwd: folders?.[0]?.uri.fsPath, env: getEnhancedEnv(folders) },
    };
    const clientOptions: LanguageClientOptions = {
      documentSelector: DOCUMENT_SELECTOR,
      initializationOptions: buildServerSettings(),
      outputChannel: this.output,
      synchronize: {
        fileEvents: [
          vscode.workspace.createFileSystemWatcher("**/codeguard.toml"),
          vscode.workspace.createFileSystemWatcher("**/.codeguard.toml"),
          vscode.workspace.createFileSystemWatcher("**/pyproject.toml"),
          vscode.workspace.createFileSystemWatcher("**/.codeguard-baseline.json"),
        ],
      },
    };
    const client = new LanguageClient("codeguard", "CodeGuard", serverOptions, clientOptions);
    this.client = client;
    try {
      await client.start();
      client.onNotification("codeguard/summaryChanged", (params: { counts: SummaryCounts }) =>
        this.summaryEmitter.fire(params.counts)
      );
      this.setState("running");
    } catch (error) {
      this.client = undefined;
      this.setState("failed");
      this.output.appendLine(`Failed to start: ${String(error)}`);
      void vscode.window.showErrorMessage(`CodeGuard language server failed to start: ${error}`);
    }
  }

  async stop(): Promise<void> {
    const client = this.client;
    this.client = undefined;
    if (client) {
      await client.stop();
    }
    this.setState("stopped");
  }

  async restart(): Promise<void> {
    await this.stop();
    await this.start();
  }

  /** Push changed editor settings to the running server (it rescans). */
  async sendSettings(): Promise<void> {
    await this.client?.sendNotification("workspace/didChangeConfiguration", {
      settings: { codeguard: buildServerSettings() },
    });
  }

  async summary(): Promise<Summary | undefined> {
    if (!this.client || !this.isRunning()) {
      return undefined;
    }
    return this.client.sendRequest<Summary>("codeguard/summary", {});
  }

  /** Apply every safe fix (in one file, or everywhere); returns the number of edits. */
  async fixAll(uri?: vscode.Uri): Promise<number> {
    if (!this.client || !this.isRunning()) {
      return 0;
    }
    const result = await this.client.sendRequest<{ edit: LspWorkspaceEdit; count: number }>(
      "codeguard/fixAll",
      uri ? { uri: uri.toString() } : {}
    );
    if (!result.count) {
      return 0;
    }
    const edit = await this.client.protocol2CodeConverter.asWorkspaceEdit(result.edit);
    const applied = await vscode.workspace.applyEdit(edit);
    return applied ? result.count : 0;
  }

  async executeServerCommand(command: string, args: unknown[] = []): Promise<unknown> {
    if (!this.client || !this.isRunning()) {
      throw new Error("CodeGuard language server is not running.");
    }
    return this.client.sendRequest("workspace/executeCommand", { command, arguments: args });
  }

  showOutput(): void {
    this.output.show(true);
  }

  dispose(): void {
    void this.stop();
    this.summaryEmitter.dispose();
    this.stateEmitter.dispose();
    this.output.dispose();
  }
}
