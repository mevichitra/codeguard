# CodeGuard Demo & Sales Playbook

> **The definitive field guide for demonstrating CodeGuard v2.0 to prospects, engineering teams, and security leaders.**  
> Covers how to run each showcase, what to highlight on screen, and the core value proposition ("what to sell").

---

## Quick Launch: Interactive Master Runner

You can launch any demo in 1 keystroke using the master runner:

```bash
# Interactive menu:
./demos/run_demo.sh

# Or run a specific demo directly:
./demos/run_demo.sh 1    # Demo 1: Inner Loop & Multi-Language Scan
./demos/run_demo.sh 2    # Demo 2: "Stop the Bleeding" Baseline Adoption
./demos/run_demo.sh 3    # Demo 3: Diff-Aware CI & SARIF Export
./demos/run_demo.sh 4    # Demo 4: Governed Suppressions & Anti-Rot Audit
./demos/run_demo.sh 5    # Demo 5: Monorepo Policy-as-Code
./demos/run_demo.sh all  # Run all 5 demos sequentially
```

---

## Showcase 1: Developer Inner-Loop & Speed (Shift-Left)

### 🎯 Target Persona
* **Primary**: Staff Engineers, Tech Leads, Application Developers.
* **Secondary**: VP of Engineering (concerned with developer velocity and context-switching).

### 💥 The Problem / Pain Point
* Traditional enterprise SAST tools (SonarQube, Checkmarx, Veracode) take 15–45 minutes to run inside heavy CI pipelines or cloud containers.
* Developers find out about security bugs days or weeks after writing the code, causing massive context-switching costs and release delays.
* Many scanners only support one language well or require bulky Docker daemons locally.

### 🚀 Command to Run
```bash
./demos/01_developer_inner_loop/run.sh
# Or direct command:
codeguard scan demos/01_developer_inner_loop/
```

### 📺 What to Highlight on Screen
1. **Sub-50ms Execution**: Notice how fast the scan completes. No spinner, no cloud delay, no database connection.
2. **Unified Multi-Language Analysis**: In a single directory pass, CodeGuard analyzes both Python (Python stdlib AST) and TypeScript/React (Tree-sitter AST).
3. **Exact Visual Pointers**: Point out the caret (`^`) directly pinpointing the offending character/sink on the source code line.
4. **Actionable Fix Guidance**: Point out the arrow `→` with copy-pasteable remediation suggestions (e.g., how to use parameterized queries instead of string concatenation, or how to replace `Math.random()` with `crypto.randomBytes()`).

### 💰 What to Sell (Value Proposition)
* **True Shift-Left**: Fix security issues at the exact moment code is written, when remediation costs 90% less than in staging or production.
* **Zero Cognitive Load**: Developers don't need a security certification to fix issues; CodeGuard tells them the exact syntax to use.
* **100% Offline & Private**: Zero code leaves the developer machine; completely safe for confidential IP, banking, healthcare, and air-gapped environments.

---

## Showcase 2: "Stop the Bleeding" Legacy Baseline (Day-1 Adoption)

### 🎯 Target Persona
* **Primary**: VP of Engineering, Engineering Directors.
* **Secondary**: AppSec Leads who struggle with getting developer buy-in.

### 💥 The Problem / Pain Point
* Rolling out security tooling on an established codebase is usually a nightmare: the initial scan finds 500+ legacy issues.
* CI immediately breaks across all engineering teams, halting sprint delivery.
* Developers mutiny, security leads are forced to disable rules, and the tool becomes shelfware.

### 🚀 Command to Run
```bash
./demos/02_legacy_baseline/run.sh
```

### 📺 What to Highlight on Screen
1. **Step 1 (The Reality)**: `codeguard scan` catches 2 high-severity legacy vulnerabilities (exit code 1).
2. **Step 2 (The Solution)**: Run `codeguard baseline create`. CodeGuard snapshots AST fingerprints into `.codeguard-baseline.json`.
3. **Step 3 (Immediate Unblock)**: Rescan with `--baseline`. Output says `✓ No findings` with exit code 0! The team can turn on CI gating on Day 1 without breaking existing builds.
4. **Step 4 (Net-New Enforcement)**: Simulate a developer submitting a PR with a new vulnerability (`new_feature.py`). CodeGuard catches **only** the new issue while silently tolerating the baseline debt.
5. **Step 5 (Ratcheting Down Debt)**: Show that as developers refactor legacy code, `codeguard baseline prune` permanently drops resolved items so old debt can never return.

### 💰 What to Sell (Value Proposition)
* **Instant Day-1 Rollout**: Zero delay to sprint cycles; no need to pause feature development to triage 500 legacy warnings.
* **Stable AST Fingerprinting**: CodeGuard fingerprints AST tokens—reformatting code or shifting line numbers does not invalidate the baseline.
* **Continuous Debt Reduction**: Establishes a ratchet mechanism that only allows security debt to decrease over time.

---

## Showcase 3: Diff-Aware CI Gating & Platform Integration

### 🎯 Target Persona
* **Primary**: DevOps Engineers, Platform Engineers, DevSecOps.
* **Secondary**: Security Operations managing GitHub Security / GitLab dashboards.

### 💥 The Problem / Pain Point
* Full scans in CI slow down PR builds, causing developer wait queues and inflated cloud CI/runner bills.
* Proprietary scanners require custom dashboards and separate logins that developers never visit.

### 🚀 Command to Run
```bash
./demos/03_ci_diff_and_sarif/run.sh
```

### 📺 What to Highlight on Screen
1. **Diff-Aware Speed**: `codeguard ci` diffs against the PR base branch (`origin/main`) and scans **only modified files**, completing in milliseconds even in massive million-line repos.
2. **GitHub Actions Inline Annotations**: Show `--format github`. The output emits `::error file=...,line=...::` workflow commands that automatically appear as red inline annotations on the GitHub PR diff view without uploading files.
3. **Standard OASIS SARIF 2.1.0**: Show `--format sarif`. Validates that CodeGuard outputs industry-standard SARIF with CWE taxonomy tags, rule descriptions, and severity scores, which directly populates the native **GitHub Code Scanning (Security tab)**.
4. **Universal Formats**: Reviewdog (`rdjson`) for automated PR comments on GitLab/Bitbucket, and JUnit (`junit`) for standard CI build reports.

### 💰 What to Sell (Value Proposition)
* **Sub-2-Second PR Checks**: Never slows down CI; eliminates runner congestion.
* **Zero Vendor Lock-In**: Integrates with existing developer tools (GitHub, GitLab, Reviewdog) without requiring a new web portal or login.
* **One-Line CI Setup**: Ready-to-use GitHub Action (`uses: mevichitra/codeguard/action@v2`).

---

## Showcase 4: Governed Suppressions & Anti-Rot Auditing

### 🎯 Target Persona
* **Primary**: CISO, Security Directors, Compliance Auditors (SOC 2, ISO 27001, HIPAA).
* **Secondary**: Tech Leads reviewing PR code.

### 💥 The Problem / Pain Point
* In most tools, developers bypass rules using `# noqa` or `# ignore` without explanation.
* Over 2–3 years, codebases fill with unmaintained waivers and hidden vulnerabilities that nobody remembers or dares to remove.
* Auditors demand proof of why security controls were waived.

### 🚀 Command to Run
```bash
./demos/04_governed_suppressions/run.sh
```

### 📺 What to Highlight on Screen
1. **Mandatory Justification (`CG-META-001`)**: Show what happens when a developer writes a bare `# codeguard: ignore`. CodeGuard suppresses the code rule but immediately flags a **Meta-Rule warning**: `[CG-META-001] Suppression comment has no reason`.
2. **Expiring Temporary Waivers (`CG-META-002`)**: Show a suppression with `until=2024-01-01`. Since the date has passed, CodeGuard reactivates the vulnerability and raises `[CG-META-002] Suppression has expired`.
3. **Centralized Waiver Auditing**: Run `codeguard suppressions list`. Show the tabular report detailing every waiver in the company: file, line, rule, reason, and status (`active`, `expired`, `unused`).
4. **Housekeeping Cleanliness**: Show `--unused` detecting dead waivers left behind after a refactor.

### 💰 What to Sell (Value Proposition)
* **Auditable Compliance**: Instant evidence for SOC 2 Type II and ISO 27001 auditors demonstrating who approved waivers and why.
* **Elimination of Security Debt Rot**: Temporary exceptions automatically expire and demand re-evaluation rather than remaining forever.
* **Peer-Review Transparency**: Reviewers immediately see whether an inline waiver includes a defensible business reason.

---

## Showcase 5: Centralized Policy & Monorepo Governance

### 🎯 Target Persona
* **Primary**: Platform Architecture Teams, Security Policy Managers.
* **Secondary**: Monorepo Maintainers.

### 💥 The Problem / Pain Point
* Enterprise repos contain multiple tiers: high-risk payment APIs, internal batch jobs, migration scripts, and test mocks.
* One-size-fits-all scanners create immense noise in test fixtures and scripts, leading developers to turn off rules entirely.

### 🚀 Command to Run
```bash
./demos/05_monorepo_policy/run.sh
```

### 📺 What to Highlight on Screen
1. **Policy-as-Code Validation**: `codeguard validate` checks syntax and rule references before deploying changes.
2. **Context-Aware Severity Remapping**: Show that SQL injection (`CG-SEC-001`) is remapped to `CRITICAL` for mission-critical services.
3. **Path Overrides (`[[overrides]]`)**: Show that for internal maintenance scripts (`scripts/**`), shell execution rules are silenced while remaining strictly enforced in core microservices.
4. **Clean Verification**: Running `--show-suppressed` reveals that CodeGuard intentionally ignored the script according to repo policy, with zero guessing.

### 💰 What to Sell (Value Proposition)
* **Single-File Governance**: Manage organizational security standards from one central `codeguard.toml` or `pyproject.toml`.
* **Zero-Noise Customization**: Tune policies per directory or service tier without duplicating configurations.

---

## Competitive Differentiation & Objection Handling

| Common Customer Objection | The Winning CodeGuard Response |
| :--- | :--- |
| **"We already have SonarQube / Veracode."** | *"Those are heavy gate scanners that take 20+ minutes in CI and get checked once a week. CodeGuard runs in <50ms inside your developer's pre-commit hook and PR diffs. CodeGuard prevents the vulnerability before your enterprise scanner even wakes up."* |
| **"Does our source code get sent to third-party servers or AI APIs?"** | *"No. CodeGuard is 100% offline and deterministic. It uses local AST and Tree-sitter parsers. Zero code leaves your developer's machine or your private CI runner. Perfect for air-gapped and high-compliance environments."* |
| **"Won't adding another security tool break our current sprint?"** | *"No, because of CodeGuard Baselines. Run `codeguard baseline create` on day 1. All existing legacy issues are frozen. CI will pass immediately and only block newly introduced bugs on active PR branches."* |
| **"Can't developers just add `# ignore` comments to bypass it?"** | *"Not without accountability. CodeGuard requires a mandatory `reason:` on every suppression, supports automated expiration dates (`until=YYYY-MM-DD`), and provides a unified CLI audit report (`codeguard suppressions list`) to review all waivers."* |
| **"How hard is it to install and configure?"** | *"It takes 30 seconds. `pipx install codeguard-cli` and `codeguard init`. No databases, no Redis, no docker containers, and no license servers to configure."* |
