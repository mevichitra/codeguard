// SPDX-License-Identifier: Apache-2.0
import * as vscode from "vscode";
import {
  DocumentSelector,
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from "vscode-languageclient/node";
import { findCodeGuardExecutable } from "./locate";

let client: LanguageClient | undefined;
let statusBarItem: vscode.StatusBarItem | undefined;

async function startLanguageServer(): Promise<void> {
  const config = vscode.workspace.getConfiguration("codeguard");
  const enabled = config.get<boolean>("enable", true);
  if (!enabled) {
    if (statusBarItem) {
      statusBarItem.hide();
    }
    return;
  }

  const command = findCodeGuardExecutable(vscode.workspace.workspaceFolders);
  if (!command) {
    if (statusBarItem) {
      statusBarItem.text = "$(shield) CodeGuard (not found)";
      statusBarItem.tooltip = "CodeGuard executable was not found.";
      statusBarItem.show();
    }
    const installAction = "Copy Install Command";
    const settingsAction = "Open Settings";
    vscode.window
      .showErrorMessage(
        "CodeGuard was not found on PATH or in workspace virtual environments. " +
          "Install it with `pipx install codeguard-cli` or `uv tool install codeguard-cli`, " +
          "or set `codeguard.path` in settings.",
        installAction,
        settingsAction
      )
      .then((selection) => {
        if (selection === installAction) {
          vscode.env.clipboard.writeText("pipx install codeguard-cli");
          vscode.window.showInformationMessage("Copied `pipx install codeguard-cli` to clipboard.");
        } else if (selection === settingsAction) {
          vscode.commands.executeCommand("workbench.action.openSettings", "codeguard.path");
        }
      });
    return;
  }

  const serverOptions: ServerOptions = {
    command,
    args: ["lsp"],
    options: {
      env: {
        ...process.env,
      },
    },
  };

  const documentSelector: DocumentSelector = [
    { scheme: "file", language: "python" },
    { scheme: "file", language: "javascript" },
    { scheme: "file", language: "javascriptreact" },
    { scheme: "file", language: "typescript" },
    { scheme: "file", language: "typescriptreact" },
  ];

  const clientOptions: LanguageClientOptions = {
    documentSelector,
    synchronize: {
      fileEvents: [
        vscode.workspace.createFileSystemWatcher("**/codeguard.toml"),
        vscode.workspace.createFileSystemWatcher("**/.codeguard.toml"),
        vscode.workspace.createFileSystemWatcher("**/pyproject.toml"),
        vscode.workspace.createFileSystemWatcher("**/.codeguard-baseline.json"),
      ],
    },
  };

  client = new LanguageClient("codeguard", "CodeGuard", serverOptions, clientOptions);

  try {
    await client.start();
    if (statusBarItem) {
      statusBarItem.text = "$(shield) CodeGuard";
      statusBarItem.tooltip = "CodeGuard Security Scanner (Click to open dashboard)";
      statusBarItem.show();
    }
  } catch (error) {
    vscode.window.showErrorMessage(`Failed to start CodeGuard language server: ${error}`);
  }
}

async function stopLanguageServer(): Promise<void> {
  if (client) {
    const activeClient = client;
    client = undefined;
    await activeClient.stop();
  }
}

async function restartLanguageServer(): Promise<void> {
  await stopLanguageServer();
  await startLanguageServer();
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.text = "$(shield) CodeGuard";
  statusBarItem.tooltip = "CodeGuard Security Scanner (Click to open dashboard)";
  statusBarItem.command = "codeguard.openDashboard";
  context.subscriptions.push(statusBarItem);

  context.subscriptions.push(
    vscode.commands.registerCommand("codeguard.openDashboard", async () => {
      if (client && client.isRunning()) {
        try {
          const activeUri = vscode.window.activeTextEditor?.document.uri.toString();
          await client.sendRequest("workspace/executeCommand", {
            command: "codeguard.openDashboard",
            arguments: activeUri ? [activeUri] : [],
          });
        } catch (err) {
          vscode.window.showErrorMessage(`Could not open CodeGuard dashboard: ${err}`);
        }
      } else {
        vscode.window.showWarningMessage(
          "CodeGuard language server is not currently running. Check configuration or restart server."
        );
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("codeguard.restartServer", async () => {
      await restartLanguageServer();
      vscode.window.showInformationMessage("CodeGuard language server restarted.");
    })
  );

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(async (event) => {
      if (
        event.affectsConfiguration("codeguard.enable") ||
        event.affectsConfiguration("codeguard.path")
      ) {
        await restartLanguageServer();
      }
    })
  );

  await startLanguageServer();
}

export async function deactivate(): Promise<void> {
  await stopLanguageServer();
  if (statusBarItem) {
    statusBarItem.dispose();
    statusBarItem = undefined;
  }
}
