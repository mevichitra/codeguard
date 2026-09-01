# CodeGuard Interactive Demos & Showcases

This directory contains interactive, ready-to-run showcases demonstrating CodeGuard v2.0 capabilities across the developer lifecycle.

## Quick Start

Launch the master interactive runner:

```bash
./demos/run_demo.sh
```

Or open the interactive HTML report menu from anywhere inside the source checkout:

```bash
codeguard run
```

This is an alias for `./demos/run_demo.sh`. Choose demos 1–5 to generate an
individual HTML report, `A` for the combined report, or `6` for the real-world
OWASP NodeGoat scan. Generated reports open in Google Chrome.

## Presentation-ready HTML report

Generate a polished, self-contained report for all showcases:

```bash
./demos/run_demo.sh --html all
```

The report is written to `demos/reports/codeguard-demo-report.html`. It includes
navigable demo and finding sections, severity/status filters, finding search,
source lines, recommended fixes, commands, scan evidence, key takeaways, a print
layout, and expandable full console output. The report opens automatically in
Google Chrome after generation. Generate one showcase or choose a custom path:

```bash
./demos/run_demo.sh --html 3
./demos/run_demo.sh --html all ./codeguard-showcase.html
```

Or run any showcase directly:

* **Demo 1**: Inner-Loop & Speed (Python + TypeScript)  
  `./demos/01_developer_inner_loop/run.sh`
* **Demo 2**: "Stop the Bleeding" Legacy Baseline Adoption  
  `./demos/02_legacy_baseline/run.sh`
* **Demo 3**: Diff-Aware CI Gating & SARIF / GitHub Actions  
  `./demos/03_ci_diff_and_sarif/run.sh`
* **Demo 4**: Governed Suppressions & Anti-Rot Auditing  
  `./demos/04_governed_suppressions/run.sh`
* **Demo 5**: Centralized Policy & Monorepo Governance  
  `./demos/05_monorepo_policy/run.sh`
* **Real-world Demo**: Scan the OWASP NodeGoat application  
  `./demos/06_real_world_nodegoat/run.sh`

The real-world demo can also be launched from the master menu with option `6`.
It is intentionally kept separate from `all` because its first run downloads an
external repository.

## Sales & Presenter Playbook

For a comprehensive guide covering customer pain points, target personas, live screen highlights, objection handling, and value propositions for each demo, see:

📖 **[DEMO_PITCH_GUIDE.md](DEMO_PITCH_GUIDE.md)**
