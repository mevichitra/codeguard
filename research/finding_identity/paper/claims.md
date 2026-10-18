# Claims and the numbers behind them

Every quantitative statement the paper can make, with its value, interval, counts and
source. Rates in percent; intervals are 95% cluster-bootstrap intervals over
repositories (10,000 resamples, seed 20261014) unless marked Wilson. Phrase the claims
as you like, but keep each number tied to the row it comes from.

Sources:

- `numbers.md`, `table_rq1.tex`, `rq1.csv`: `paper_kit.py` over the corpus replays
  (CodeGuard: `results/corpus-v3`; Bandit: `results/corpus-bandit`, B101 left out of the
  table and kept as `bandit_all_rules`).
- `tables.md`, `pooled.csv`, `per_repo.csv`: `stats` over `results/corpus-v3`.
- `rq2.csv`, `fig_rq2.pdf`: `paper_kit.py --transform` over `results/transform/`.

Runs: CodeGuard 2.2.0 and Bandit 1.9.4, corpus pinned 2026-10-14, 200 first-parent
commit pairs per repository, replayed on 2026-10-17.

## Setup facts

| # | Fact | Value | Source |
|---|---|---|---|
| S1 | Repositories | 35 (25 Python, 10 JavaScript/TypeScript) | `corpus.csv` |
| S2 | Commit pairs replayed | 7,000 (CodeGuard); 5,000 (Bandit, Python only) | `numbers.md` |
| S3 | Persisting / introduced findings, CodeGuard | 23,237 / 1,974 | `numbers.md` |
| S4 | Persisting / introduced findings, Bandit without B101 | 15,718 / 1,097 | `numbers.md` |
| S5 | Persisting / introduced findings, Bandit with B101 | 174,853 / 13,024 | `numbers.md` (`bandit_all_rules`) |
| S6 | B101's share of Bandit's persisting / introduced findings | 91.0% (159,135) / 91.6% (11,927); 98% of B101 findings are in test code | `numbers.md`, rule table of *Bandit (all rules)* |
| S6b | Without B101, Bandit's findings are mostly hard-coded password strings | B105 35.9% and B106 31.0% of persisting findings; 76% and 99% of them in test code | `numbers.md`, rule table of *Bandit* |
| S7 | Persisting CodeGuard findings on edited lines | 142 of 23,237 (0.6%) | `pooled.csv`, `false_new_edited` den |
| S8 | Persisting CodeGuard findings in renamed files | 287 (1.2%), in 8 repositories | `numbers.md` |
| S9 | Replay time, CodeGuard batch | 1,100 s wall clock on 4 cores for 35 repositories | batch log |
| S10 | SonarQube tracker port check | 20,000 generated cases, 0 mismatches against the unmodified Java tracker | PR #56; `fidelity/sonar_cases.py` |
| S11 | Semgrep port check | all 716 `match_based_id` values emitted during the Flask and DefectDojo replays reproduced | PR #56 |

## RQ1: real histories

| # | Claim | Value | Source |
|---|---|---|---|
| C1 | Line numbers report about half of all persisting findings as new | `line` 52.6 (48.5–57.6) on CodeGuard findings; 55.0 (49.6–61.6) on Bandit findings | `table_rq1.tex` |
| C2 | Content-based schemes report 0.3–4.4% as new | CodeGuard findings: `sonar` 0.4 (0.3–0.6), `sonar_branch` 0.6 (0.3–1.0), `codeguard` 1.8 (0.7–3.4), `line_text` 1.9 (0.8–3.5), `github` 3.1 (2.0–4.9), `bandit` 4.4 (3.1–6.3) | `table_rq1.tex` |
| C3 | The ranking holds on Bandit's own findings | `sonar` 0.27 (0.11–0.52), `codeguard` 0.42 (0.23–0.72), `line_text` 0.78 (0.52–1.08), `github` 1.93 (1.10–3.05) | `numbers.md`, Bandit section |
| C4 | Renamed files: every key scheme includes the path and reports all their findings as new | 287/287 for `line`, `line_text`, `github`, `codeguard`, `bandit` | `numbers.md` (`false_new_renamed`) |
| C5 | Renames are a minority of findings but most of the content schemes' false-new reports | 1.2% of persisting findings; 69% of `codeguard`'s false-new reports (287 of 417), 65% of `line_text`'s (287/440), 39% of `github`'s (287/730) | `numbers.md` (counts) |
| C6 | On files that keep their path, the content schemes are close | `sonar` 0.36 (0.24–0.53), `codeguard` 0.57 (0.39–0.80), `line_text` 0.67 (0.48–0.91), `github` 1.93 (1.62–2.32) | `numbers.md` (`false_new_same_path`) |
| C7 | SonarQube's identity depends on the analysis type across renames | renamed files: pull-request mode 2.8 (1.7–8.3), 8/287; branch mode 20.2 (4.3–62.3), 58/287. Overall 0.39 vs 0.61 | `numbers.md` |
| C8 | Edited lines are where every scheme fails | false-new on the 142 edited-line findings: `line_text` 100, `github` 87.3, `codeguard` 74.6, `sonar` 63.4, `bandit` 23.9 (Bandit ignores location and code) | `pooled.csv`, `false_new_edited` |
| C9 | **Set membership hides new findings** | Bandit's baseline on Bandit findings without B101: 29.2 (20.1–40.9) hidden, 320 of 1,097; with B101: 51.2 (42.5–65.2), 6,670/13,024; on CodeGuard findings: 20.0 (14.1–28.6), 394/1,974 | `table_rq1.tex`, `numbers.md` |
| C9b | It is not a test-fixture effect | without B101, outside test code: 36.3% of 273 introduced findings in 22 repositories hidden (in test code: 26.8% of 824). Other schemes outside test code: `github` 1.8, `codeguard` 2.9, `sonar` 5.9. No interval: a sensitivity check (see note C) | note C |
| C10 | Every other scheme hides far fewer | on Bandit findings without B101: `line` 1.9, `codeguard` 2.5, `github` 3.3, `sonar` 4.5, `line_text` 6.0; on CodeGuard findings 0.8–1.9 | `table_rq1.tex` |
| C11 | Schemes that survive more edits collide more | collision rate, CodeGuard findings: `github` 2.1 (1.1–3.5), `line_text` 17.4 (14.0–21.3), `codeguard` 18.6 (12.9–24.8), `sonar` 20.3 (16.5–24.4), `bandit` 54.2 (44.4–62.5) | `table_rq1.tex` |
| C12 | The pooled rate hides a skewed spread; one repository dominates `codeguard`'s rate | Ghost: `codeguard` 19.9% of 687 persisting findings (renames from `.js` to `.ts`), `sonar` 1.0, `sonar_branch` 1.7. Per-repository median of `codeguard`: 0.48 | `per_repo.csv`, `numbers.md` |
| C13 | Findings within a repository are correlated, so per-finding intervals are too narrow | `line_text` false-new 1.89: Wilson 1.73–2.08 against cluster bootstrap 0.80–3.51 | `pooled.csv` |

Caution when pairing C11 with hidden rates: `codeguard`'s hidden rate (1.9, 0.9–3.5) and
`github`'s (0.8, 0.2–1.9) have overlapping intervals, so collisions cost "tends to hide
more", not "hides more".

## RQ2: controlled changes

Setup: ten transformations, each applied to one target finding in each of 40 sampled
files per repository (seeded), in the 25 Python repositories at their pinned commits.
Cases per transformation range from 150 (`extract_helper`) to 937 (`insert_top`); a
transformation that does not fit a file is skipped with a recorded reason. Rates are
pooled over repositories (`rq2.csv` has the cluster-bootstrap intervals). Fig. 1 omits
`sonar_branch`: no transformation renames a file, so it equals `sonar` in every cell.

| # | Claim | Value | Source |
|---|---|---|---|
| R1 | Every single-key scheme has a blind spot | `line`: insert_top 99.1, move_function 96.2, extract_helper 97.3, reformat 85.9. `github`: insert_below 77.5 (its hash reads up to 100 characters forward). `codeguard`: rename_function 100, extract_helper 100, rename_local 97.9 (the enclosing scope and the statement). `line_text`/`github`: change_literal 100/99.6, rename_local 100/100 | `rq2.csv`, Fig. 1 |
| R2 | Literal masking works | change_literal: `codeguard` 0, against `line_text` 100 and `github` 99.6 | `rq2.csv` |
| R3 | SonarQube's fallbacks on different evidence make it the most robust | 0 on insert_top, insert_below, move_function, change_literal and extract_helper (a later pass matches the same line hash elsewhere in the file); still loses rename_function 59.0, reformat 17.6, rename_local 9.8 | `rq2.csv` |
| R4 | Function-level findings break text schemes on renames | rename_function: `line_text`/`github` 59.5. 485 of the 822 cases are complexity, nesting and parameter-count findings (CG-QUAL-003/004/005) reported on the `def` line, which the rename changes | `results/transform/*/cases.jsonl` (note D) |
| R5 | A copy of a finding is hidden; which copy depends on pairing order | duplicate_above: hidden 100 for every scheme except `github` 11.5; duplicate_below: `github` 88.5 (its forward hash moves to the copy), `bandit` 97.3 (set membership), all others 0.4–5.4 | `rq2.csv` |
| R6 | Locations inside messages break message-based identity | insert_top moves no code, yet `bandit` reports 2.5% as new: CG-SEC-001, -013 and -014 put source line numbers in their messages ("built on line N", "(line N)") | `cases.jsonl`; `src/codeguard/rules/security/_taint.py`, `cg_sec_001_sql_injection.py` |

Caution: reformat runs black at 79 columns, so how much it changes depends on how each
repository was formatted before; the row measures that edit, not formatting in general.

## Notes

A. **Why B101 is left out of Bandit's column.** B101 flags every `assert`, and almost all
of them are in tests; many projects skip it there. Its message never varies, so
Bandit's set-membership baseline hides every new `assert` once one is baselined, which
would dominate the hidden rate. The paper reports Bandit without B101 and gives the
all-rules figure (C9) as a sensitivity check.

C. **C9b** counts introduced Bandit findings (B101 excluded) whose path contains `test`
or `conftest` (the same test-code rule as `paper_kit.TEST_PATH_PARTS`), from
`results/corpus-bandit/*/findings.jsonl`. If the paper keeps it, add the split to
`paper_kit.py` so it gets an interval.

D. **R4** counts scored `rename_function` cases by rule from
`results/transform/*/cases.jsonl` (`target_outcomes.line_text == "false_new"`).

E. **Still to do before submission.**
- Manual check of the ground truth on a stratified sample (for Threats): a sample file
  for labelling can be generated from `findings.jsonl`.
- Verify every related-work reference in `outline.md` before citing it.
- Decide whether `sonar` or `sonar_branch` is "SonarQube" in the abstract. Branch mode
  is what compares a long-lived baseline on the main branch; pull-request mode is what
  gates a PR.
