// SPDX-License-Identifier: Apache-2.0
import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";

/**
 * Checks whether a given file path exists and is accessible.
 */
function isExecutable(filePath: string): boolean {
  try {
    const stat = fs.statSync(filePath);
    if (!stat.isFile()) {
      return false;
    }
    // On Windows, checking existence is usually sufficient.
    // On POSIX, check executable bit.
    if (process.platform === "win32") {
      return true;
    }
    fs.accessSync(filePath, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

/**
 * Locates the `codeguard` executable using the following resolution order:
 * 1. User/Workspace configuration setting (`codeguard.path`)
 * 2. Workspace root virtual environments (`.venv/bin/codeguard`, `venv/bin/codeguard`)
 * 3. System `PATH`
 */
export function findCodeGuardExecutable(
  workspaceFolders?: readonly vscode.WorkspaceFolder[]
): string | undefined {
  // 1. Check explicit setting
  const config = vscode.workspace.getConfiguration("codeguard");
  const configuredPath = config.get<string>("path", "").trim();
  if (configuredPath) {
    if (path.isAbsolute(configuredPath) && isExecutable(configuredPath)) {
      return configuredPath;
    }
    // If relative path given in config, check against workspace folders
    if (workspaceFolders && workspaceFolders.length > 0) {
      for (const folder of workspaceFolders) {
        const resolved = path.resolve(folder.uri.fsPath, configuredPath);
        if (isExecutable(resolved)) {
          return resolved;
        }
      }
    }
    if (isExecutable(configuredPath)) {
      return configuredPath;
    }
  }

  // 2. Check workspace virtual environments
  const candidateRelPaths: string[] =
    process.platform === "win32"
      ? [
          path.join(".venv", "Scripts", "codeguard.exe"),
          path.join("venv", "Scripts", "codeguard.exe"),
          path.join(".venv", "codeguard.exe"),
        ]
      : [
          path.join(".venv", "bin", "codeguard"),
          path.join("venv", "bin", "codeguard"),
          path.join(".venv", "codeguard"),
        ];

  if (workspaceFolders && workspaceFolders.length > 0) {
    for (const folder of workspaceFolders) {
      for (const rel of candidateRelPaths) {
        const candidate = path.resolve(folder.uri.fsPath, rel);
        if (isExecutable(candidate)) {
          return candidate;
        }
      }
    }
  }

  // 3. Check system PATH
  const envPath = process.env.PATH || "";
  const pathDirs = envPath.split(path.delimiter);
  const exeNames =
    process.platform === "win32"
      ? ["codeguard.exe", "codeguard.cmd", "codeguard.bat", "codeguard"]
      : ["codeguard"];

  for (const dir of pathDirs) {
    if (!dir) {
      continue;
    }
    for (const exe of exeNames) {
      const candidate = path.join(dir, exe);
      if (isExecutable(candidate)) {
        return candidate;
      }
    }
  }

  return undefined;
}
