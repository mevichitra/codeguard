# CodeGuard

Fast, offline static analysis for **Python, JavaScript, and TypeScript**. It finds
**security** vulnerabilities (with source-to-sink taint tracking), **performance**
problems, and **code-quality** risks, fixes the safe ones for you, and works at every
gate of your workflow: editor, pre-commit, PR/CI, and scheduled audit, all from one
config file.

**Status: 2.2.0 (beta).** Rule IDs, the `Finding` / JSON schema, config keys, and exit
codes have been a stable contract since 2.0. Upgrading never changes a pipeline's exit
code: `scan` and `ci` run security rules unless you opt into more. See the
[migration notes](docs/migration-v2.md) if you used the 0.1 alpha.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![CI](https://github.com/mevichitra/codeguard/actions/workflows/ci.yml/badge.svg)](https://github.com/mevichitra/codeguard/actions)
[![PyPI](https://img.shields.io/pypi/v/codeguard-cli.svg)](https://pypi.org/project/codeguard-cli/)

---

## What it does

```text
app.py:11:5  [CG-SEC-011] CRITICAL  Untrusted input reaches a shell command
    11 |     os.system(cmd)
             ^
  ↳ line 9: Untrusted input: flask request.form
  ↳ line 9: Flows through: host = request.form["host"]
  ↳ line 10: Flows through: cmd = "ping -c 1 " + host
  → Run the program with an argument list and shell=False ...
```

Every finding has a stable rule ID, a severity, a CWE / OWASP mapping for security
rules, a precise location, and a fix suggestion. Many also carry a **safe autofix**.

| Category | Rules | Highlights |
|---|---|---|
| **Security** | 25 | Taint-tracked SQL / shell / `eval` / path traversal / open redirect (Python). Pattern rules for injection, XSS, unsafe deserialization, hardcoded secrets, weak hashes, disabled TLS verification, insecure randomness, Express open redirect / path traversal, prototype pollution. |
| **Performance** | 10 | List-literal membership in loops, quadratic string building, regexes compiled in loops, `await` in loops, spread in `reduce`, JSON deep clones. |
| **Quality** | 9 | Mutable defaults, swallowed exceptions, cyclomatic complexity, nesting depth, parameter count, loose equality, empty `catch`, `var`. |

Full list: [docs/rules](docs/rules/index.md), or `codeguard list-rules`.

---

## Install

```bash
pipx install codeguard-cli      # or: uv tool install codeguard-cli
pip install codeguard-cli       # into the current environment
```

The PyPI project is `codeguard-cli`; the command is `codeguard`. It needs Python 3.10+.
No database, no network, and no code leaves the machine.

From source:

```bash
git clone https://github.com/mevichitra/codeguard && cd codeguard
pip install -e ".[dev]"
```

---

## Usage

```bash
codeguard scan src/                                  # security rules (default)
codeguard scan src/ --category performance           # or quality, or several
codeguard scan src/ --fix-dry-run                    # preview safe autofixes as a diff
codeguard scan src/ --fix                            # apply them
codeguard scan src/ --format sarif -o results.sarif  # json, sarif, github, rdjson, junit
codeguard scan src/ --fail-on high                   # exit 1 only for high or critical
codeguard explain CG-SEC-011                         # what a rule catches and how to fix it
```

Exit codes: `0` clean, `1` findings at or above `--fail-on`, `2` usage error,
`3` config error, `4` internal error.

### Suppressions

```python
query = f"SELECT * FROM t WHERE id = {uid}"  # codeguard: ignore[CG-SEC-001] reason: uid is an int until=2026-12-31
```

A suppression without a reason, or past its `until=` date, is itself reported
(`CG-META-001` / `002`). Audit them with `codeguard suppressions list`.

### Configuration

`codeguard.toml` (or `[tool.codeguard]` in `pyproject.toml`). Run `codeguard init` for a
starter file.

```toml
[codeguard]
exclude    = ["tests/fixtures/**", "**/*.min.js"]
categories = ["security", "performance", "quality"]   # default: ["security"]
fail_on    = "high"
baseline   = ".codeguard-baseline.json"

[codeguard.rules]
disable = ["CG-QUAL-104"]

[codeguard.rules.CG-QUAL-003]
max_complexity = 20          # rule options: see `codeguard explain <ID>`
```

See [configuration](docs/configuration.md), [baselines](docs/baseline.md),
[autofix](docs/autofix.md), and [taint tracking](docs/taint.md).

---

## CI integration

```yaml
- uses: mevichitra/codeguard/action@v2    # diff-aware scan + SARIF upload to code scanning
```

`codeguard ci` scans only the files changed since the base branch and applies the
baseline. Pre-commit hooks and a Docker image are also available. See
[docs/ci.md](docs/ci.md).

---

## Editor integrations

The language server (`codeguard lsp`) and the extensions put every finding in the editor
with **severity-coloured diagnostics, hovers that show the taint path, quick fixes,
one-click suppressions, and fix-all on save**. Editors show security, performance, and
quality findings by default; CI keeps the project's categories.

- **VS Code** ([`editors/vscode`](editors/vscode)): a Findings sidebar grouped by
  severity, category, or file; live status-bar counts; a Security Overview panel; fix
  all in the workspace; SARIF export; and a getting-started walkthrough.
- **Zed** ([`editors/zed`](editors/zed)): native diagnostics and Project Diagnostics,
  `lsp.codeguard` settings passthrough, `code_actions_on_format` fix-all, and a
  local Markdown dashboard.
- **Neovim, Helix, and other LSP clients:** run `codeguard lsp`. See
  [docs/editors.md](docs/editors.md) for configuration and the custom
  `codeguard/summary` protocol.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). A new rule is one module, a vulnerable and a safe
fixture (plus a `fixed` fixture if it has an autofix), a test, and a docs page.

## Roadmap

Phase 1 (2.2, this release) added taint tracking, the performance and quality packs,
autofix, and the editor UX. Next come JavaScript / TypeScript taint tracking, same-file
function summaries, Semgrep-compatible custom rules, more security rules (SSRF, XXE,
ReDoS, JWT, insecure cookies), Marketplace / Open VSX publishing, and standalone
binaries. Details in [docs/roadmap.md](docs/roadmap.md).

---

## License

Apache-2.0. See [LICENSE](LICENSE).

Contributions are accepted under the [Developer Certificate of Origin](https://developercertificate.org/) (DCO). Sign your commits with `git commit -s`.
