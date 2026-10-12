# Working on CodeGuard with Claude Code

## Authorship and sign-off

All work in this repository is authored by the maintainer, not by Claude.

- Commit as the maintainer: `Vichitra Attri <mevichitra@gmail.com>`. If
  `git config user.name` / `user.email` show anything else (for example
  `Claude <noreply@anthropic.com>`), set them for this repository before
  committing.
- Always sign off commits (DCO): `git commit -s`. Every commit must carry a
  `Signed-off-by:` line matching the author.
- Never add `Co-Authored-By: Claude ...`, `Claude-Session: ...`, or any other
  Claude attribution trailer to a commit message.
- Never add "Generated with Claude Code" or a Claude session link to a pull
  request title or description.

`.claude/settings.json` turns off Claude Code's automatic commit and PR
attribution; the rules above still apply when writing messages by hand.
