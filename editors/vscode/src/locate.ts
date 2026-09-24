// SPDX-License-Identifier: Apache-2.0
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

/**
 * Checks whether a given file path exists and is executable.
 */
function isExecutable(filePath: string): boolean {
  try {
    const stat = fs.statSync(filePath);
    if (!stat.isFile()) {
      return false;
    }
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
 * Builds an enhanced PATH string containing standard user tool directories.
 * This is crucial on macOS where GUI-launched VS Code has a minimal PATH.
 */
export function getEnhancedPath(
  workspaceFolders?: readonly vscode.WorkspaceFolder[]
): string {
  const home = os.homedir();
  const extraDirs: string[] = [];

  // 1. Workspace virtual environments
  if (workspaceFolders) {
    for (const folder of workspaceFolders) {
      if (process.platform === "win32") {
        extraDirs.push(path.join(folder.uri.fsPath, ".venv", "Scripts"));
        extraDirs.push(path.join(folder.uri.fsPath, "venv", "Scripts"));
      } else {
        extraDirs.push(path.join(folder.uri.fsPath, ".venv", "bin"));
        extraDirs.push(path.join(folder.uri.fsPath, "venv", "bin"));
      }
    }
  }

  // 2. Standard global and user installation paths
  if (process.platform === "win32") {
    const localAppData = process.env.LOCALAPPDATA || path.join(home, "AppData", "Local");
    const appData = process.env.APPDATA || path.join(home, "AppData", "Roaming");
    extraDirs.push(path.join(localAppData, "Programs", "Python", "Python312", "Scripts"));
    extraDirs.push(path.join(localAppData, "Programs", "Python", "Python311", "Scripts"));
    extraDirs.push(path.join(localAppData, "Programs", "Python", "Python310", "Scripts"));
    extraDirs.push(path.join(appData, "Python", "Python312", "Scripts"));
    extraDirs.push(path.join(appData, "Python", "Python311", "Scripts"));
    extraDirs.push(path.join(appData, "Python", "Python310", "Scripts"));
    extraDirs.push(path.join(home, ".local", "bin"));
    extraDirs.push(path.join(home, ".cargo", "bin"));
  } else {
    extraDirs.push(path.join(home, ".local", "bin"));
    extraDirs.push(path.join(home, ".cargo", "bin"));
    extraDirs.push("/opt/homebrew/bin");
    extraDirs.push("/opt/homebrew/sbin");
    extraDirs.push("/usr/local/bin");
    extraDirs.push("/usr/local/sbin");
    extraDirs.push(path.join(home, ".pyenv", "shims"));
    extraDirs.push(path.join(home, "miniconda3", "bin"));
    extraDirs.push(path.join(home, "miniforge3", "bin"));
    extraDirs.push(path.join(home, "anaconda3", "bin"));
  }

  const existingPath = process.env.PATH || "";
  const existingDirs = existingPath.split(path.delimiter);
  const combined = [...extraDirs, ...existingDirs];
  const uniqueDirs = Array.from(new Set(combined.filter((d) => d && fs.existsSync(d))));

  return uniqueDirs.join(path.delimiter);
}

/**
 * Returns environment variables with enhanced PATH for spawning CodeGuard LSP.
 */
export function getEnhancedEnv(
  workspaceFolders?: readonly vscode.WorkspaceFolder[]
): NodeJS.ProcessEnv {
  return {
    ...process.env,
    PATH: getEnhancedPath(workspaceFolders),
  };
}

/**
 * Locates the `codeguard` executable using prioritized lookup.
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

  // 3. Check enhanced search PATH (including ~/.local/bin, Homebrew, etc.)
  const enhancedPath = getEnhancedPath(workspaceFolders);
  const pathDirs = enhancedPath.split(path.delimiter);
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
