// SPDX-License-Identifier: Apache-2.0
//! CodeGuard for Zed: starts `codeguard lsp` and passes Zed settings through to it.
//!
//! Users configure the server in Zed's `settings.json`:
//!
//! ```jsonc
//! "lsp": {
//!   "codeguard": {
//!     "binary": { "path": "/path/to/codeguard" },          // optional
//!     "initialization_options": {
//!       "severityMap": { "medium": "error" },
//!       "categories": { "quality": false },
//!       "rules": { "disable": ["CG-QUAL-104"] }
//!     }
//!   }
//! }
//! ```

use zed_extension_api::{self as zed, serde_json::json, serde_json::Value, settings::LspSettings};

const SERVER_NAME: &str = "codeguard";
const UNIX_CANDIDATES: [&str; 2] = [".venv/bin/codeguard", "venv/bin/codeguard"];
const WINDOWS_CANDIDATES: [&str; 2] = [".venv/Scripts/codeguard.exe", "venv/Scripts/codeguard.exe"];
const INSTALL_HINT: &str = "CodeGuard was not found. Install it with `pipx install codeguard-cli` \
     or `uv tool install codeguard-cli` (or into the project's .venv), or set \
     lsp.codeguard.binary.path in Zed settings, then restart Zed.";

struct CodeGuardExtension;

/// Defaults Zed sends; anything the user sets in `initialization_options` wins.
fn default_initialization_options() -> Value {
    json!({
        "client": "zed",
        // Zed has no webview: rule links open the local Markdown dashboard.
        "codeDescription": "dashboard",
        "scanWorkspaceOnStartup": true
    })
}

/// Recursively overlay `overlay` onto `base` (objects merge, everything else replaces).
fn merge_json(base: &mut Value, overlay: Value) {
    match (base, overlay) {
        (Value::Object(base_map), Value::Object(overlay_map)) => {
            for (key, value) in overlay_map {
                match base_map.get_mut(&key) {
                    Some(existing) => merge_json(existing, value),
                    None => {
                        base_map.insert(key, value);
                    }
                }
            }
        }
        (slot, value) => *slot = value,
    }
}

/// Workspace virtual-environment paths to probe, for the given platform.
fn venv_candidates(windows: bool) -> &'static [&'static str] {
    if windows {
        &WINDOWS_CANDIDATES
    } else {
        &UNIX_CANDIDATES
    }
}

fn join_root(root: &str, relative: &str, windows: bool) -> String {
    let sep = if windows { '\\' } else { '/' };
    let rel = if windows {
        relative.replace('/', "\\")
    } else {
        relative.to_string()
    };
    format!("{}{}{}", root.trim_end_matches(['/', '\\']), sep, rel)
}

impl CodeGuardExtension {
    fn settings(worktree: &zed::Worktree) -> LspSettings {
        LspSettings::for_worktree(SERVER_NAME, worktree).unwrap_or_default()
    }

    /// `binary.path` setting, then the project's virtualenv, then `PATH`.
    fn find_binary(worktree: &zed::Worktree, settings: &LspSettings) -> Option<String> {
        if let Some(path) = settings.binary.as_ref().and_then(|b| b.path.clone()) {
            return Some(path);
        }
        let (os, _) = zed::current_platform();
        let windows = matches!(os, zed::Os::Windows);
        let root = worktree.root_path();
        // read_text_file is the only existence probe the API offers; it succeeds for any
        // readable file, including binaries' launcher scripts and .exe shims.
        for relative in venv_candidates(windows) {
            if worktree.read_text_file(relative).is_ok() {
                return Some(join_root(&root, relative, windows));
            }
        }
        worktree.which("codeguard")
    }
}

impl zed::Extension for CodeGuardExtension {
    fn new() -> Self {
        Self
    }

    fn language_server_command(
        &mut self,
        _language_server_id: &zed::LanguageServerId,
        worktree: &zed::Worktree,
    ) -> zed::Result<zed::Command> {
        let settings = Self::settings(worktree);
        let command =
            Self::find_binary(worktree, &settings).ok_or_else(|| INSTALL_HINT.to_string())?;
        let (arguments, extra_env) = match settings.binary {
            Some(binary) => (binary.arguments, binary.env),
            None => (None, None),
        };
        let args = arguments
            .filter(|a| !a.is_empty())
            .unwrap_or_else(|| vec!["lsp".to_string()]);
        let mut env = worktree.shell_env();
        if let Some(extra) = extra_env {
            env.extend(extra);
        }
        Ok(zed::Command { command, args, env })
    }

    fn language_server_initialization_options(
        &mut self,
        _language_server_id: &zed::LanguageServerId,
        worktree: &zed::Worktree,
    ) -> zed::Result<Option<Value>> {
        let mut options = default_initialization_options();
        if let Some(user) = Self::settings(worktree).initialization_options {
            merge_json(&mut options, user);
        }
        Ok(Some(options))
    }

    fn language_server_workspace_configuration(
        &mut self,
        _language_server_id: &zed::LanguageServerId,
        worktree: &zed::Worktree,
    ) -> zed::Result<Option<Value>> {
        // Same shape as initialization options, under a `codeguard` section, so a change
        // to `lsp.codeguard.settings` in Zed reaches the server without a restart.
        let mut section = default_initialization_options();
        let settings = Self::settings(worktree);
        if let Some(user) = settings.initialization_options {
            merge_json(&mut section, user);
        }
        if let Some(user) = settings.settings {
            merge_json(&mut section, user);
        }
        Ok(Some(json!({ "codeguard": section })))
    }
}

zed::register_extension!(CodeGuardExtension);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merge_overlays_nested_objects() {
        let mut base = default_initialization_options();
        merge_json(
            &mut base,
            json!({ "codeDescription": "help", "severityMap": { "medium": "error" } }),
        );
        assert_eq!(base["client"], "zed");
        assert_eq!(base["codeDescription"], "help");
        assert_eq!(base["severityMap"]["medium"], "error");

        merge_json(&mut base, json!({ "severityMap": { "low": "off" } }));
        assert_eq!(base["severityMap"]["medium"], "error");
        assert_eq!(base["severityMap"]["low"], "off");
    }

    #[test]
    fn non_object_overlay_replaces() {
        let mut base = json!({ "rules": { "disable": ["A"] } });
        merge_json(&mut base, json!({ "rules": { "disable": ["B", "C"] } }));
        assert_eq!(base["rules"]["disable"], json!(["B", "C"]));
    }

    #[test]
    fn candidates_and_paths_per_platform() {
        assert_eq!(venv_candidates(false)[0], ".venv/bin/codeguard");
        assert_eq!(venv_candidates(true)[0], ".venv/Scripts/codeguard.exe");
        assert_eq!(
            join_root("/repo/", ".venv/bin/codeguard", false),
            "/repo/.venv/bin/codeguard"
        );
        assert_eq!(
            join_root("C:\\repo", ".venv/Scripts/codeguard.exe", true),
            "C:\\repo\\.venv\\Scripts\\codeguard.exe"
        );
    }
}
