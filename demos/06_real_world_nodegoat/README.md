# Real-world repository demo: OWASP NodeGoat

This demo scans the public [OWASP NodeGoat](https://github.com/OWASP/NodeGoat)
training application. NodeGoat is intentionally vulnerable and is designed to
teach OWASP Top 10 risks in a realistic Node.js codebase.

The checkout is pinned to commit `c5cb68a7084e4ae7dcc60e6a98768720a81841e8`
for repeatable results. The repository checkout and all generated reports are
Git-ignored.

## Run the complete demo

From the CodeGuard project root:

```bash
./demos/06_real_world_nodegoat/run.sh
```

On the first run, the script downloads NodeGoat. It then creates:

- `reports/nodegoat.txt` — terminal-friendly output
- `reports/nodegoat.json` — structured findings
- `reports/nodegoat.sarif` — CI/security-platform integration
- `reports/nodegoat-report.html` — presentation-friendly finding explorer

The HTML report opens automatically in Google Chrome. To generate it without
opening a browser:

```bash
./demos/06_real_world_nodegoat/run.sh --no-open
```

## Run each stage manually

```bash
# 1. Download or reset the pinned repository checkout
./demos/06_real_world_nodegoat/setup.sh

# 2. Human-readable scan
.venv/bin/codeguard scan \
  demos/06_real_world_nodegoat/.workspace/NodeGoat \
  --config demos/06_real_world_nodegoat/codeguard.toml \
  --jobs 1 --show-suppressed --exit-zero

# 3. JSON report
.venv/bin/codeguard scan \
  demos/06_real_world_nodegoat/.workspace/NodeGoat \
  --config demos/06_real_world_nodegoat/codeguard.toml \
  --jobs 1 --format json --show-suppressed --exit-zero \
  -o demos/06_real_world_nodegoat/reports/nodegoat.json

# 4. SARIF report
.venv/bin/codeguard scan \
  demos/06_real_world_nodegoat/.workspace/NodeGoat \
  --config demos/06_real_world_nodegoat/codeguard.toml \
  --jobs 1 --format sarif --show-suppressed --exit-zero \
  -o demos/06_real_world_nodegoat/reports/nodegoat.sarif
```

## Demo scope

The policy scans first-party JavaScript and excludes vendored browser assets,
tests, database-reset fixtures, and dependencies. This keeps the conversation
focused on actionable application findings instead of third-party noise.

> NodeGoat is intentionally insecure. Do not deploy it as a production service.

