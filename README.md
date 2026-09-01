# CodeGuard

Fast, offline static analysis that finds security anti-patterns in **Python, JavaScript, and TypeScript** — and drops into every gate of your workflow (editor, pre-commit, PR/CI, scheduled audit) from a single config file.

**Status: 2.0 (beta).** Rule IDs, the `Finding`/JSON schema, config keys, and exit codes are a stable contract from 2.0. See [migration notes](docs/migration-v2.md) if you used the 0.1 alpha.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![CI](https://github.com/mevichitra/codeguard/actions/workflows/ci.yml/badge.svg)](https://github.com/mevichitra/codeguard/actions)
[![PyPI](https://img.shields.io/pypi/v/codeguard-cli.svg)](https://pypi.org/project/codeguard-cli/)

---

## What it does

CodeGuard scans **Python, JavaScript, and TypeScript** and reports security findings. Each finding has a stable rule ID, severity, CWE/OWASP mapping, and a plain-English fix suggestion.

Current rules (see [docs/rules/](docs/rules/) for detail):

| ID | What it catches | Severity | CWE | Languages |
|---|---|---|---|---|
| CG-SEC-001 | SQL built with f-strings / `%` / `.format()` | HIGH | CWE-89 | Python |
| CG-SEC-002 | Hardcoded passwords, API keys, tokens | HIGH | CWE-798 | Python |
| CG-SEC-003 | `eval()` / `exec()` on non-literal input | HIGH | CWE-95 | Python |
| CG-SEC-004 | `pickle.loads` / `yaml.load` without SafeLoader | HIGH | CWE-502 | Python |
| CG-SEC-005 | `subprocess(..., shell=True)` with non-literal args | HIGH | CWE-78 | Python |
| CG-SEC-101 | `eval` / `new Function` / string timers on dynamic input | HIGH | CWE-95 | JS, TS |
| CG-SEC-102 | `child_process.exec` with a dynamic command | HIGH | CWE-78 | JS, TS |
| CG-SEC-103 | `innerHTML` / `document.write` assigned a non-literal | HIGH | CWE-79 | JS, TS |
| CG-SEC-104 | `dangerouslySetInnerHTML` with a non-literal value | HIGH | CWE-79 | JS, TS |
| CG-SEC-105 | Hardcoded passwords, API keys, tokens | HIGH | CWE-798 | JS, TS |
| CG-SEC-106 | `Math.random()` used for a token / secret / id | MEDIUM | CWE-338 | JS, TS |

### What it does not do (yet)

- Baseline / diff scanning, a CI-native command, packaged distribution (planned for v2.0)
- AI-generated-code detection (deferred to a post-2.0 experimental module)
- Web dashboard or REST API

---

## Install

```bash
pipx install codeguard-cli      # or: uv tool install codeguard-cli
pip install codeguard-cli       # into the current environment

# or from source:
git clone https://github.com/mevichitra/codeguard
cd codeguard
pip install -e ".[dev]"
```

The PyPI project is `codeguard-cli`; the installed command is `codeguard`.

Requires Python 3.10+. No database, no Redis, no Docker needed.

---

## Usage

```bash
# Scan a file or directory
codeguard scan myproject/

# Output as JSON
codeguard scan myproject/ --format json

# Output as SARIF (for GitHub code scanning)
codeguard scan myproject/ --format sarif > results.sarif

# Only run specific rules
codeguard scan myproject/ --rule CG-SEC-001 --rule CG-SEC-002

# Only report HIGH and above
codeguard scan myproject/ --severity high
```

Example output (human format):

```
myproject/auth.py:12:4  [CG-SEC-001] HIGH  SQL query built with string formatting
  → Use parameterized queries: cursor.execute("SELECT ... WHERE id = %s", (user_id,))

myproject/config.py:5:0  [CG-SEC-002] HIGH  Hardcoded secret: password
  → Load secrets from environment variables or a secrets manager.

2 findings  (2 high, 0 medium, 0 low)
```

Exit codes: `0` = no findings, `1` = findings found, `2` = error.

### Inline suppression

```python
query = f"SELECT * FROM users WHERE id = {uid}"  # codeguard: ignore[CG-SEC-001]
```

Suppressed findings still appear with `suppressed: true` in JSON/SARIF output.

### Config file

Place a `codeguard.toml` in your project root:

```toml
[codeguard]
exclude = ["tests/", "migrations/"]
severity = "medium"   # ignore findings below this level

[codeguard.rules]
disabled = ["CG-SEC-002"]  # not yet
```

_(Config file support is on the roadmap; not yet implemented.)_

---

## CI integration

### GitHub Actions

```yaml
- name: Run CodeGuard
  run: |
    pip install codeguard-cli
    codeguard scan src/ --format sarif > codeguard.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: codeguard.sarif
```

## Zed editor integration

CodeGuard includes a development extension for Zed that displays findings as
native editor diagnostics while keeping all analysis local.

```bash
# Install this checkout so Zed can find the command.
pipx install -e .
# or: uv tool install -e .
```

In Zed, open **Extensions**, select **Install Dev Extension**, and choose the
[`editors/zed`](editors/zed) directory. The extension starts `codeguard lsp`,
scans the workspace on startup, and refreshes open files after edits.

The LSP can also be started directly by any compatible editor:

```bash
codeguard lsp
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a rule or file a bug.  
Adding a rule requires: one rule file + two test fixtures (vulnerable + safe). See the [rule authoring guide](CONTRIBUTING.md#adding-a-rule).

---

## Project status and roadmap

**2.0 (beta).** Rule IDs, the `Finding` / JSON schema, config keys, and the exit-code
contract are stable. Full details in [the changelog](CHANGELOG.md) and
[docs/](https://mevichitra.github.io/codeguard/).

On the roadmap:

1. Light intraprocedural taint tracking (source → sink, sanitizer-aware) to cut false positives further
2. A Semgrep-compatible YAML rule subset for custom rules
3. Autofix (`--fix`) for the safe-fix rules
4. Standalone single-file binaries and a Homebrew tap
5. An LSP server for editor integration
6. Optional, offline AI-assisted triage (confidence + rationale, no code leaves the machine)

---

## License

Apache-2.0. See [LICENSE](LICENSE).

Contributions are accepted under the [Developer Certificate of Origin](https://developercertificate.org/) (DCO). Sign your commits with `git commit -s`.
