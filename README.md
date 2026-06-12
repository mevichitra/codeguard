# CodeGuard

Static analysis for Python code, with a focus on security patterns common in AI-generated code.

**Status: early alpha.** The rule engine and CLI work; five security rules are implemented and tested. Do not use in production yet.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![CI](https://github.com/codeguard-ai/codeguard/actions/workflows/ci.yml/badge.svg)](https://github.com/codeguard-ai/codeguard/actions)

---

## What it does

CodeGuard scans Python source files and reports security and quality findings. Each finding has a stable rule ID, severity, CWE/OWASP mapping, and a plain-English fix suggestion.

Current rules (see [docs/rules/](docs/rules/) for detail):

| ID | What it catches | Severity | CWE |
|---|---|---|---|
| CG-SEC-001 | SQL built with f-strings / `%` / `.format()` | HIGH | CWE-89 |
| CG-SEC-002 | Hardcoded passwords, API keys, tokens | HIGH | CWE-798 |
| CG-SEC-003 | `eval()` / `exec()` on non-literal input | HIGH | CWE-78 |
| CG-SEC-004 | `pickle.loads` / `yaml.load` without SafeLoader | HIGH | CWE-502 |
| CG-SEC-005 | `subprocess(..., shell=True)` with non-literal args | HIGH | CWE-78 |

### What it does not do (yet)

- Multi-language support (Python only)
- AI-generated-code detection (planned as an experimental, isolated module)
- Web dashboard or REST API (planned for later layers)

---

## Install

```bash
pip install codeguard          # once published to PyPI
# or from source:
git clone https://github.com/codeguard-ai/codeguard
cd codeguard
pip install -e ".[dev]"
```

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
    pip install codeguard
    codeguard scan src/ --format sarif > codeguard.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: codeguard.sarif
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a rule or file a bug.  
Adding a rule requires: one rule file + two test fixtures (vulnerable + safe). See the [rule authoring guide](CONTRIBUTING.md#adding-a-rule).

---

## Project status and roadmap

CodeGuard is in **early alpha**. The public interfaces (rule IDs, `Finding` schema, CLI flags) are not yet stable across versions.

Planned work, roughly in order:

1. More security rules (secrets scanning improvements, prompt-injection patterns in LLM-calling code, hardcoded IPs/URLs)
2. `codeguard.toml` config support
3. Suppression audit report
4. FastAPI wrapper (thin layer over the library — no logic in the API)
5. Experimental AI-generated-code heuristics (isolated module, clearly labelled)
6. JavaScript/TypeScript support

---

## License

Apache-2.0. See [LICENSE](LICENSE).

Contributions are accepted under the [Developer Certificate of Origin](https://developercertificate.org/) (DCO). Sign your commits with `git commit -s`.