# Instructions for coding agents

These rules apply to every AI coding agent working in this repository (Claude Code,
Codex, Copilot and any other).

## Commit authorship

- Commits are authored and committed by the maintainer, **Vichitra Attri
  <mevichitra@gmail.com>**, never by an agent. Before the first commit, set:

  ```bash
  git config user.name "Vichitra Attri"
  git config user.email "mevichitra@gmail.com"
  ```

- Never commit under an agent's or a bot's name or address (for example `Claude`,
  `noreply@anthropic.com`, `Codex`, `Copilot`, or any `[bot]` account), and never add
  `Co-authored-by:` or other trailers that name an agent.
- Sign off (`git commit -s`, see [CONTRIBUTING.md](CONTRIBUTING.md)) only as Vichitra
  Attri.
- If a commit was made under another identity, fix its author, committer and
  `Signed-off-by:` before pushing.
