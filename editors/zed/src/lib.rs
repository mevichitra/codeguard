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
        let command = worktree.which("codeguard").ok_or_else(|| {
            "CodeGuard was not found on PATH. Install it with `pipx install codeguard-cli` \
             or `uv tool install codeguard-cli`, then restart Zed."
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
