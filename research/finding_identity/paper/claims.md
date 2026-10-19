# Claims and the numbers behind them

Every quantitative statement the paper can make, with its value, interval, counts and
source. Rates in percent; intervals are 95% cluster-bootstrap intervals over
repositories (10,000 resamples, seed 20261014) unless marked Wilson. Phrase the claims
as you like, but keep each number tied to the row it comes from.

Sources:

- `numbers.md`, `table_rq1.tex`, `table_gate.tex`, `rq1.csv`: `paper_kit.py` over the
  corpus replays (CodeGuard: `results/corpus-v4`; Bandit: `results/corpus-bandit-v2`,
  B101 left out of the tables and kept as `bandit_all_rules`). Both replays use the
  move-aware ground truth (`linemap.py`, mapping kind `relocated`).
- `tables.md`, `pooled.csv`, `per_repo.csv`: `stats` over `results/corpus-v4`.
- `rq2.csv`, `fig_rq2.pdf`: `paper_kit.py --transform` over `results/transform/`.
- `ground_truth_check/agreement.md`: `gt_agreement.py --results results/corpus-v4`; its
  last two sections score the replay's ground truth against the adjudicated verdicts.

Runs: CodeGuard 2.2.0 and Bandit 1.9.4, corpus pinned 2026-10-14, 200 first-parent
commit pairs per repository. The earlier replays without move detection
(`results/corpus-v3`, `results/corpus-bandit`) are kept for the before/after rows (S12).

## Setup facts

| # | Fact | Value | Source |
|---|---|---|---|
| S1 | Repositories | 35 (25 Python, 10 JavaScript/TypeScript) | `corpus.csv` |
| S2 | Commit pairs replayed | 7,000 (CodeGuard); 5,000 (Bandit, Python only) | `numbers.md` |
| S3 | Persisting / introduced findings, CodeGuard | 23,245 / 1,966 | `numbers.md` |
| S4 | Persisting / introduced findings, Bandit without B101 | 15,746 / 1,069 | `numbers.md` |
| S5 | Persisting / introduced findings, Bandit with B101 | 174,909 / 12,968 | `numbers.md` (`bandit_all_rules`) |
| S6 | B101's share of Bandit's persisting / introduced findings | 91.0% (159,163) / 91.8% (11,899); 98% of B101 findings are in test code | `numbers.md`, rule table of *Bandit (all rules)* |
| S6b | Without B101, Bandit's findings are mostly hard-coded password strings | B105 36.0% and B106 31.0% of persisting findings; 76% and 99% of them in test code | `numbers.md`, rule table of *Bandit* |
| S7 | Persisting CodeGuard findings on edited / relocated lines | 143 (0.6%) edited, 7 relocated, of 23,245 | `pooled.csv`, `false_new_edited` and `false_new_relocated` den |
| S8 | Persisting CodeGuard findings in renamed files | 287 (1.2%), in 8 repositories | `numbers.md` |
| S9 | Replay time, CodeGuard batch | 1,281 s wall clock on 4 cores for 35 repositories (other jobs were running, so an upper bound) | batch log of `corpus-v4` |
| S10 | SonarQube tracker port check | 20,000 generated cases, 0 mismatches against the unmodified Java tracker | PR #56; `fidelity/sonar_cases.py` |
| S11 | Semgrep port check | 87,916 of the 87,924 `match_based_id` values Semgrep emitted over the 35-repository run reproduced; the 8 others (lines 183 and 184 of calcom's `apps/web/playwright/booking-pages.e2e.ts`, rule `detect-non-literal-regexp`) were a port bug: two taint results at one sink that Semgrep numbers in source order (`RuleMatches.add`) but reports in message order. Fixed; on 3,671 IDs from 550 calcom files the fixed port has 0 mismatches. The `semgrep` scheme uses Semgrep's emitted IDs, so no result changes. Earlier: all 716 in the Flask and DefectDojo replays, all 7,051 in the four-repository pilot | `results/corpus-semgrep/*/analyzer.json` (`port_checked`, `port_mismatches`), `_logs/calcom.log`; PR #56 |
| S15 | Semgrep run | Semgrep 1.180.0 with 587 rules from the opengrep-rules fork of semgrep-rules at `f1d2b562` (LGPL-2.1 with the Commons Clause), on all 35 repositories, 7,000 pairs: 57,166 persisting and 4,328 introduced findings, 298 persisting in renamed files in 11 repositories; 0 failed batches; 91 file versions timed out and 106 had parse problems (skipped, as for the other analyzers) | `numbers.md` (Semgrep section), `analyzer.json` |
| S12 | Move detection changes few findings | of v3's 1,974 introduced CodeGuard findings, 8 become persisting (1,966 left); of Bandit's 1,097 without B101, 28 (1,069 left). Persisting findings mapped as relocated: 7 (CodeGuard), 52 (Bandit, all rules) | `numbers.md` of v3 and v4; `known_relocated` in `results/corpus-v4/*/summary.json` and `results/corpus-bandit-v2/*/summary.json` |
| S13 | The large-block fallback never touched a finding | v1's position-by-position pairing of blocks over 4,000 cells: 0 of 25,211 CodeGuard and 0 of 187,877 Bandit records (counted with an instrumented v1 replay, not committed). v2 aligns fully up to 40,000 cells and in a band beyond; 0 findings in banded blocks | `known_banded`, `introduced_banded` in the v4 and bandit-v2 summaries |
| S14 | Collision keys of the matcher schemes | `sonar`, `sonar_branch`: rule, path and line hash (the key of SonarQube's last pass); `bandit`: the `Issue.__eq__` tuple (issue text, severity, CWE, confidence, file, test name and test ID) | `schemes.py`, `trackers.py` |

## RQ1: real histories

| # | Claim | Value | Source |
|---|---|---|---|
| C1 | Line numbers report about half of all persisting findings as new | `line` 52.6 (48.5–57.6) on CodeGuard findings; 55.0 (49.6–61.7) on Bandit findings | `table_rq1.tex` |
| C2 | Content-based schemes report 0.4–4.4% as new | CodeGuard findings: `sonar` 0.4 (0.3–0.6), `sonar_branch` 0.6 (0.3–1.0), `codeguard` 1.8 (0.7–3.4), `line_text` 1.9 (0.8–3.5), `github` 3.1 (2.0–4.9), `bandit` 4.4 (3.1–6.3) | `table_rq1.tex` |
| C2b | The order is backed by paired differences | CodeGuard findings, a − b in points: `sonar` − `codeguard` −1.40 (−2.92 to −0.37); `codeguard` − `line_text` −0.12 (−0.19 to −0.06); `github` − `codeguard` 1.35 (1.14 to 1.60); `sonar` − `sonar_branch` −0.22 (−0.61 to −0.01). All exclude 0 | `numbers.md`, paired differences, *CodeGuard findings* |
| C3 | The ranking holds on Bandit's own findings | `sonar` 0.27 (0.11–0.52), `codeguard` 0.47 (0.25–0.79), `line_text` 0.89 (0.59–1.29), `github` 2.01 (1.12–3.21); paired: `sonar` − `codeguard` −0.20 (−0.33 to −0.09), `codeguard` − `line_text` −0.42 (−0.59 to −0.23), `github` − `codeguard` 1.54 (0.85 to 2.47) | `numbers.md`, Bandit section |
| C4 | Renamed files: every key scheme includes the path and reports all their findings as new | 287/287 for `line`, `line_text`, `github`, `codeguard`, `bandit` | `numbers.md` (`false_new_renamed`) |
| C5 | Renames are a minority of findings but most of two content schemes' false-new reports | 1.2% of persisting findings; 69% of `codeguard`'s false-new reports (287 of 418), 64% of `line_text`'s (287/445), 39% of `github`'s (287/732) | `numbers.md` (counts) |
| C6 | On files that keep their path, the content schemes are close | `sonar` 0.37 (0.24–0.54), `codeguard` 0.57 (0.39–0.81), `line_text` 0.69 (0.50–0.94), `github` 1.94 (1.62–2.33); paired: `codeguard` − `sonar` 0.20 (0.11 to 0.31) | `numbers.md` (`false_new_same_path`) |
| C7 | SonarQube's identity depends on the analysis type across renames | renamed files: pull-request mode 2.8 (1.7–8.3), 8/287; branch mode 20.2 (4.3–62.3), 58/287. Overall 0.40 vs 0.61. The interval rests on the 8 repositories with renames; no resample was dropped for an empty denominator | `numbers.md` (rates; dropped resamples) |
| C8 | Edited lines are where every content scheme reports findings as new | false-new (not mispaired) on the 143 edited-line findings: `line_text` 100, `github` 87.4, `codeguard` 74.8, `sonar` 63.6, `bandit` 23.8 (Bandit ignores location and code). `sonar`'s 91 are 83 in same-path files and 8 in renamed files | `pooled.csv`, `false_new_edited` |
| C8b | Mispairing is rare except where locations or messages collide | mispaired, CodeGuard findings: `github` 0.1, `sonar` 0.2, `line_text` 0.2, `codeguard` 0.3, `line` 2.8, `bandit` 3.7 | `table_rq1.tex` |
| C9 | **Set membership hides new findings** | Bandit's baseline on Bandit findings without B101: 27.3 (18.7–39.0) hidden, 292 of 1,069; with B101: 51.0 (42.3–64.9), 6,614/12,968; on CodeGuard findings: 19.6 (13.8–28.3), 386/1,966 | `table_rq1.tex`, `numbers.md` |
| C9b | It is not a test-fixture effect | without B101, outside test code: 35.1% of 268 introduced findings (94) in 22 repositories hidden (in test code: 24.7% of 801). Other schemes outside test code: `github` 0.7, `codeguard` 1.1, `line_text` 2.6, `sonar` 4.1. No interval: a sensitivity check (see note C) | note C |
| C10 | Every other scheme hides far fewer | on Bandit findings without B101: `codeguard` 0.7, `line` 2.0, `github` 2.0, `sonar` 2.0, `line_text` 5.2; on CodeGuard findings 0.5–1.5. Paired, Bandit − each other scheme excludes 0 on every finding set. **Upper bounds**: see G4 | `table_rq1.tex`, `numbers.md` |
| C11 | Schemes that survive more edits collide more | collision rate, CodeGuard findings: `github` 2.1 (1.1–3.5), `line_text` 17.4 (14.0–21.3), `codeguard` 18.6 (12.9–24.8), `sonar` 20.3 (16.5–24.4), `bandit` 54.2 (44.4–62.5) | `table_rq1.tex` |
| C11b | Collisions cost hidden findings | `codeguard` hides 1.02 points more than `github` on CodeGuard findings (0.57 to 1.66), though it hides 1.31 fewer on Bandit's (−2.77 to −0.10) | `numbers.md`, paired differences |
| C12 | The pooled rate hides a skewed spread; one repository dominates `codeguard`'s rate | Ghost: `codeguard` 19.9% of 687 persisting findings (renames from `.js` to `.ts`), `sonar` 1.0, `sonar_branch` 1.7. Per-repository median of `codeguard`: 0.48 | `per_repo.csv`, `numbers.md` |
| C13 | Findings within a repository are correlated, so per-finding intervals are too narrow | `line_text` false-new 1.91: Wilson 1.75–2.10 against cluster bootstrap 0.81–3.54 | `pooled.csv` |

## Semgrep's findings (third analyzer)

Findings from third-party rules, not written for this study. Rates are in the one-column
table `table_rq1_semgrep.tex`. The manual check did not sample these findings.

| # | Claim | Value | Source |
|---|---|---|---|
| M1 | The false-new order of the content schemes holds on Semgrep's findings | `sonar` 0.5 (0.3–0.7), `codeguard` 1.4 (0.8–2.1), `line_text` 1.8 (1.1–2.7), `github` 3.2 (2.2–4.3); `line` 56.3 (52.5–59.9). Paired: `sonar` − `codeguard` −0.88 (−1.47 to −0.45), `codeguard` − `line_text` −0.45 (−0.86 to −0.02), `github` − `codeguard` 1.81 (1.18 to 2.45) | `table_rq1_semgrep.tex`, `numbers.md` |
| M2 | Bandit's baseline hides Semgrep's new findings too | hidden 22.4 (16.0–31.3), 971 of 4,328; gate miss 26.1 (19.5–33.0), 184 of 704 pairs; every non-Semgrep content scheme's gate misses at most 1.0 | `numbers.md` |
| M3 | **Semgrep's own ID hides new findings** | `semgrep` hidden 12.1 (7.4–18.6), 524 of 4,328, against 0.6–2.2 for the other content schemes; gate miss 5.1 (3.5–6.9), 36 of 704; false-new 1.4 (0.9–2.1) | `numbers.md` |
| M4 | Mechanism (from the code, not measured per finding) | `match_based_id` hashes the rule's patterns with their bindings, the path and the rule, then numbers equal keys in file order, so a new equal match placed before an old one takes its ID: the `duplicate_above` case of RQ2 | `schemes.py` (`semgrep_match_based_ids`); Semgrep `rule_match.py` |
| M5 | Semgrep's collision rate is not defined | the ordinal makes every ID in a file unique; shown as "--" | `table_rq1_semgrep.tex` |

## The gate

A gate runs on each commit pair and fails when the scheme reports any finding of the
pair's changed files as new; it should fail when the pair introduces a finding. Miss:
pairs that introduce a finding on which the gate is silent, over pairs that introduce
one. Alarm: pairs that introduce none on which it fails, over those pairs. A hidden
finding is *masked* when its pair's gate fails anyway and *silent* otherwise (masked +
silent = hidden).

| # | Claim | Value | Source |
|---|---|---|---|
| K1 | A gate built on Bandit's baseline misses a large share of the commits that add findings | miss rate of `bandit`: CodeGuard findings 13.9 (9.9–18.3), 70 of 504 pairs; CodeGuard security rules 26.4 (16.9–36.8), 43 of 163; Bandit findings without B101 34.1 (24.5–44.8), 90 of 264; Bandit with B101 59.5 (49.8–67.5), 437/735 | `table_gate.tex`, `numbers.md` (`gate_miss`) |
| K2 | Every other scheme's gate almost never misses | CodeGuard findings 0.0–1.0 (`sonar` 1.0, 5/504; `codeguard` 0.2, 1/504); security rules 0.0–1.2; Bandit findings 0.0 for every scheme but `bandit`. Paired: `bandit` − each other excludes 0 on every finding set | `table_gate.tex`, `numbers.md` |
| K2b | SonarQube's gate misses more than `codeguard`'s, but that rests on doubtful hidden findings | `sonar` − `codeguard` miss rate 0.79 points (0.18 to 1.67) on CodeGuard findings; its 7 silent hidden findings come from a hidden rate that the manual check found mostly persisting (G4: 7 of 8 sampled). Do not claim SonarQube's gate is worse; its miss rate is likely overstated | `numbers.md`; `agreement.md` |
| K3 | False alarms: line numbers fire on a fifth of quiet commits | alarm rate, CodeGuard findings: `line` 20.0 (16.6–23.5), `bandit` 5.1 (4.1–6.2), `github` 2.1 (1.5–2.8), all others ≤ 1.0. Bandit findings: `line` 14.7, `github` 1.5, others ≤ 0.4 | `table_gate.tex` |
| K4 | What the content schemes hide is mostly masked; what Bandit hides is mostly silent | CodeGuard findings: `codeguard` 30 hidden = 29 masked + 1 silent; `github` 9 + 1; `sonar` 15 + 7; `bandit` 386 = 180 masked + 206 silent. Bandit findings: `bandit` 292 = 77 masked + 215 silent (20.1%, 12.4–31.7) | `numbers.md` (`hidden_masked`, `hidden_silent`) |
| K5 | Pairs that introduce a finding | CodeGuard 504 of 7,000; CodeGuard security rules 163 of 7,000; Bandit without B101 264 of 5,000; with B101 735 of 5,000 | `table_gate.tex` caption, `numbers.md` |

Caution on K2b and K4: a masked finding still trips the gate, but the report points the
developer at another finding.

## Long spans (drift)

Three anchors per repository (200, 300 and 400 first-parent commits behind the pin; 105
anchors), each compared with the commit k steps later, k in {1, 10, 50, 100, 200}, with
the line maps chained through every commit in between (move-aware line map). CodeGuard
findings. Source: `results/drift-v2`, `drift_kit report`. The manual check did not cover
long spans.

| # | Claim | Value | Source |
|---|---|---|---|
| D1 | Renames accumulate over long spans | at k = 200: 3,813 of 36,325 persisting findings (10.5%) in 1,000 renamed files; at k = 1: 0 | `numbers_drift.md`, *Ground truth per span* and the renamed-files denominators |
| D2 | Path-keyed schemes lose those findings; SonarQube keeps them | false new at k = 200: `codeguard` 12.2 (1.7–29.6), `bandit` 14.5 (4.1–31.6), `github` 14.9 (4.0–31.9), `line_text` 18.4 (2.7–35.0), `sonar` 1.5 (0.7–2.9), `sonar_branch` 1.8 (0.9–3.3), `line` 65.0 (56.3–74.1) | `numbers_drift.md`, *False-new rate* |
| D3 | On files that keep their path the content schemes stay close | k = 200: `sonar` 1.6 (0.7–3.2), `codeguard` 1.9 (1.0–3.7), `bandit` 4.4 (3.6–5.5), `github` 4.9 (3.3–7.7), `line_text` 8.8 (1.5–19.2) | `numbers_drift.md`, *files that kept their path* |
| D4 | Bandit's baseline hides about a third of new findings from k = 50 on | 30.9 (14.5–51.5) at 50, 38.3 (17.1–58.1) at 100, 33.5 (14.5–54.4) at 200 | `numbers_drift.md`, *Hidden rate* |
| D5 | Other hidden rates at long spans are upper bounds | at k = 50: `codeguard` 15.2 (1.3–37.2), `sonar` 14.5 (0.8–36.6), `github` 13.3 (0.0–35.5); at k = 200: `github` 3.4, `codeguard` 5.1, `sonar` 6.1, `line_text` 0.9. Chained ground truth unchecked by hand | `numbers_drift.md` |
| D6 | Soundness fix in drift mode | a file deleted and re-added at the same path no longer breaks its chain (`readded_files` counted) | `drift.py`, `tests/test_drift.py` |

## Ground-truth check

A manual check on 100 sampled findings, drawn from `results/corpus-v3`; the procedure,
including a flaw in its first round, is in `ground_truth_check/README.md`, the scores in
`ground_truth_check/agreement.md`. The verdicts are fixed; the last sections of
`agreement.md` score the move-aware ground truth of `results/corpus-v4` against them.

| # | Claim | Value | Source |
|---|---|---|---|
| G1 | The ground truth is reliable for persisting findings | holds for 59 of 60 sampled pairs: 98.3% (Wilson 91.1–99.7), with and without move detection; human and LLM rater agree on 59 of 60 | `agreement.md` |
| G2 | It is weaker for introduced findings | move-aware: holds for 32 of 40, 80.0% (65.2–89.5); without move detection 30 of 40, 75.0% (59.8–85.8) | `agreement.md`, *Ground truth of the replays* and *Adjudicated* |
| G3 | Its errors sit where a scheme matched an "introduced" finding | `new_but_matched`: holds for 12 of 20, 60.0% (38.7–78.1); `agree_new`: 20 of 20. Move detection fixed 3 of the 10 earlier errors (F049, F059, F092). 7 remaining are rewrites below the 0.6 similarity threshold (an initializer, a reworded message, a declaration joined onto one line). One new disagreement, F041, rests on an LLM-only verdict and is open (see note F) | `agreement.md`, `adjudicated.json` |
| G4 | So SonarQube's hidden rate is an upper bound; the others now need no correction in the sample | corrected hidden rate on CodeGuard findings: `sonar` 1.12 → 0.14 (range 0.03–0.53): 7 of the 8 sampled findings it "hid" persisted. Every sampled finding that `line_text` (6), `github` (2) and `codeguard` (6) still hide was confirmed new | `agreement.md`, *Hidden rates after correcting* |
| G5 | Bandit's hidden rate barely moves | of its 386 hidden CodeGuard findings, 338 are in `agree_new`, where the ground truth held 20 of 20; at most the other 48 could be ground-truth errors (19.6% would fall to no less than about 17%) | `agreement.md`; stratum counts from `results/corpus-v4` |
| G6 | Threshold rules make "same finding" a question about the analyzer, not the line | three sampled complexity and nesting findings sit on an unchanged `def` line yet are new: the commit pushed the function over the limit elsewhere (verified by re-running the rule on both versions) | `adjudicated.json` (F036, F065, F076) |

How to describe the check: the human rater labelled the 60 pairs and confirmed each of
the 14 ground-truth errors the LLM rater flagged; the 27 introduced findings the LLM rater
confirmed as new had no human check. Report the LLM rater as an LLM. Cohen's kappa is
not informative here (the human rater confirmed every pair, so chance agreement is
total); report raw agreement instead.

Scope: the check sampled CodeGuard findings only. Bandit's own findings (C9's 27.3%,
C10's Bandit-findings column) were not checked, so say that their hidden rates rest on
the same ground truth without a manual check.

Caution on G4: the corrected rate scales a scheme's hidden count by the share of its
sampled matches that are truly new, from 2 to 8 sampled findings per scheme. Quote it as
an estimate with its range, and keep the uncorrected rates in Table II.

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
`results/corpus-bandit-v2/*/findings.jsonl`. If the paper keeps it, add the split to
`paper_kit.py` so it gets an interval.

D. **R4** counts scored `rename_function` cases by rule from
`results/transform/*/cases.jsonl` (`target_outcomes.line_text == "false_new"`).

F. **F041 is open.** The move-aware ground truth maps F041 (arches
`permission-designer.js`, CG-QUAL-104, old line 92 → new 148) as relocated; its
adjudicated verdict "new" came from the LLM rater alone. The statement is identical and
unique in both versions, so the ground truth is probably right. If a human rules it
persisting, G2 becomes 33/40 (82.5%) and G3 13/20.

E. **Still to do before submission.**
- Verify every related-work reference in `outline.md` before citing it.
- A human ruling on F041 (note F).
- Abstract: both SonarQube modes are named, so no choice between `sonar` and
  `sonar_branch` is needed there.
