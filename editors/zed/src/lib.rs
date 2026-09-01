use zed_extension_api as zed;

struct CodeGuardExtension;

impl zed::Extension for CodeGuardExtension {
    fn new() -> Self {
        Self
    }

    fn language_server_command(
        &mut self,
        _language_server_id: &zed::LanguageServerId,
        worktree: &zed::Worktree,
    ) -> zed::Result<zed::Command> {
        let command = worktree.which("codeguard").or_else(|| {
            let relative = ".venv/bin/codeguard";
            worktree
                .read_text_file(relative)
                .ok()
                .map(|_| format!("{}/{relative}", worktree.root_path()))
        });
        let command = command.ok_or_else(|| {
            "CodeGuard was not found on PATH or at .venv/bin/codeguard. Install it with \
             `pipx install codeguard-cli` or `uv tool install codeguard-cli`, then restart Zed."
                .to_string()
        })?;

        Ok(zed::Command {
            command,
            args: vec!["lsp".to_string()],
            env: worktree.shell_env(),
        })
    }
}

zed::register_extension!(CodeGuardExtension);
