# Paper outline: finding identity across code changes

Material for a 6-page IEEE conference paper (two columns, 10 pt). This file plans the
paper; the prose is written by the author. Every number the paper states is listed in
[claims.md](claims.md) with the file it comes from, and the tables and figures are
generated into this directory (see [Regenerating](#regenerating)).

Working title: *Same Finding, New Commit? Measuring How Static Analysis Tools Track
Findings Across Code Changes*

## Page budget

| Section | Pages | Holds |
|---|---:|---|
| Abstract | — | about 150 words |
| I. Introduction | 0.75 | problem, gap, RQs, contributions |
| II. Identity schemes | 0.6 | Table I (schemes) |
| III. Method | 1.2 | ground truth, metrics, corpus, ports and their checks, transformations |
| IV. RQ1: real histories | 1.1 | Table II (rates with CIs), the rename split, SonarQube's two modes |
| V. RQ2: controlled changes | 0.8 | Fig. 1 (invariance matrix heatmap) |
| VI. Implications | 0.4 | guidance for tool builders |
| VII. Threats to validity | 0.35 | |
| VIII. Related work | 0.35 | |
| IX. Conclusion | 0.15 | data and code availability |
| References | 0.3 | about 12 entries |

Two tables and one figure fit; a second figure (per-repository spread) only if Table I
shrinks. Drift (long spans) and Semgrep get one sentence each in VII or IX, or are left
for a longer version: their samples are small (one anchor per repository; Semgrep on two
repositories).

## Research questions

- **RQ1.** How often do the identity schemes of real tools report a persisting finding
  as new, or hide a new finding, over real commit histories?
- **RQ2.** Which kinds of code change break which schemes?

## I. Introduction

1. Baselines, suppressions, "fail only on new findings" CI gates and alert
   de-duplication all assume a tool can tell that a finding in version *n+1* is the one
   it reported in version *n*. When it cannot, old findings come back as new (noise,
   broken baselines) or new findings are taken for old ones (**hidden**, the costly
   error for a security gate).
2. Every tool solves this differently (line numbers, line hashes, multi-pass trackers,
   fingerprints of the matched code, set membership), and the choice is rarely
   documented or measured.
3. Gap: earlier work built trackers for one tool or used tracking to study developers;
   no study compares the methods shipped tools use, on the same findings, against an
   independent ground truth.
4. Contributions:
   - a replay harness that scores identity schemes against a diff-based ground truth;
   - faithful ports of the identity methods of SonarQube, Bandit, Semgrep and GitHub
     code scanning, each checked against the original tool;
   - RQ1 on 35 web applications (7,000 commit pairs), RQ2 with ten controlled
     transformations;
   - the finding that ⟨headline, see claims C1–C4⟩;
   - the data and code (Apache-2.0).

## II. Identity schemes (Table I)

One row per scheme: what the identity is built from, whether it includes the path,
pairing rule (key equality in line order, multi-pass, set membership), source.

- `line`: rule, path, line number (the naive baseline).
- `line_text`: rule, path, exact line text.
- `github`: GitHub code scanning's `primaryLocationLineHash` (rolling hash over 100
  non-blank characters from the line start) plus an occurrence index.
- `codeguard`: enclosing scope plus the normalized statement (literals masked, comments
  and whitespace removed). Ablations `cg_no_scope`, `cg_no_mask`, `cg_raw` go in the
  text or a footnote, not the table, unless space allows.
- `sonar` / `sonar_branch`: SonarQube's six-pass tracker (line, line hash, message,
  11-line block hashes for code moves). The two modes differ only across renamed files:
  pull-request analyses take renames from the SCM; branch analyses accept a rename only
  if their own file move detection does (line counts within 0.84–1.18×, line-hash
  similarity ≥ 85).
- `bandit`: `bandit -b baseline.json`: same text, severity, CWE, confidence, file and
  test; no location; set membership (one baselined issue hides any number of equal new
  ones).
- `semgrep`: `match_based_id` (rule patterns with metavariable bindings, path, rule,
  ordinal). One sentence; measured on two repositories only.

## III. Method

- **Ground truth.** Per changed file, a line diff maps old lines to new: unchanged lines
  map exactly ("moved"), lines in a replaced block pair when similarity ≥ 0.6
  ("edited"). An old and a new finding are the same when they have the same rule and the
  old line maps to the new line. Renames follow `git diff -M`.
- **Outcomes.** known_ok, mispaired, false_new, false_known (hidden), new_ok. Metrics:
  false-new rate (over persisting findings), hidden rate (over introduced findings),
  mispair rate, collision rate.
- **Corpus.** 35 open-source web applications (25 Python: Django 16, Flask 4, FastAPI 2,
  Pyramid, web.py, Frappe; 10 JavaScript/TypeScript: Express 5, NestJS 3, Next.js 2),
  pinned commits, selected by written criteria (≥ 200 first-parent commits in two years,
  OSI licence, ≥ 100 analysable back-end files, no committed build output). The last
  200 first-parent commit pairs of each.
- **Findings.** CodeGuard 2.2.0 (security, performance, quality rules) on all 35;
  Bandit 1.9.4 on the 25 Python repositories, so each tool's method is also measured on
  its own tool's findings.
- **Ports and their checks** (the reviewers' first question):
  - SonarQube tracker: the unmodified Java sources at the pinned tag, compiled into a
    harness; 20,000 generated cases, 0 mismatches.
  - Semgrep: all 716 IDs Semgrep emitted during the replays reproduced.
  - Bandit: live `bandit -b` runs agree with the port.
  - GitHub: port of `fingerprints.ts`; its tests compare against hashes produced by
    running the original `fingerprints.ts` on two reference inputs (duplicates, CRLF,
    CR-only and blank lines).
- **Statistics.** Pooled rates with cluster-bootstrap 95% CIs over repositories (10,000
  resamples): findings within a repository are correlated, so Wilson intervals are too
  narrow (show one example in a footnote). Medians and IQR per repository.
- **RQ2 transformations.** Ten edits with known effect on identity, applied one at a time
  to one target finding: reformat, insert_top, insert_below, rename_local,
  rename_function, move_function, change_literal, extract_helper, duplicate_above,
  duplicate_below. Each returns an exact line map (the ground truth by construction).
  Applied with libcst only where safe (rules listed in the README).

## IV. RQ1 results (Table II)

Table II: per scheme, false-new rate (all; same path; renamed), hidden rate, collision
rate, each with its bootstrap CI. Then three findings, in this order:

1. Line numbers lose about half of all persisting findings; every content-based scheme
   loses about 1–3% (C1).
2. **The path inside the key is the largest single cause of false-new reports** for
   content-based schemes: renamed files hold ⟨C2⟩% of persisting findings but ⟨C2⟩% of
   their false-new reports (C2). SonarQube keeps them in pull-request mode and loses
   ⟨C3⟩ in branch mode.
3. **Set membership hides new findings**: Bandit's baseline hides ⟨C4⟩% of genuinely new
   findings on its own findings (⟨C4⟩% on CodeGuard's), because equality ignores location
   and multiplicity (C4).

One sentence on the trade-off: schemes that survive more edits collide more
(`codeguard` ⟨C5⟩% collisions against `github` ⟨C5⟩%).

## V. RQ2 results (Fig. 1)

Fig. 1: heatmap, transformations × schemes, false-new rate (and hidden rate for the two
duplicate transformations). Read it as "each scheme has a blind spot":

- `line` breaks on every move; `github` on edits *below* the line (it reads forward);
  scoped schemes on renames of the enclosing function and on extraction; text schemes on
  changed literals unless they mask them.
- Duplicates: schemes pair equal keys in line order, so a copy *above* a finding is
  taken for it (hidden) and the original reported as new; GitHub's forward-reading hash
  fails the other way.

## VI. Implications

For tool builders: keep the path out of the key or make it rename-aware; pair
one-to-one, never by set membership; prefer a multi-pass matcher with a fallback on code
moves to a single key; mask literals; report collisions. For users: a "new findings
only" gate built on set membership can hide new vulnerabilities.

## VII. Threats to validity

- Ground truth is a line diff: a finding whose line is rewritten beyond the similarity
  threshold counts as removed plus introduced. Mitigation: a manual check of a stratified
  sample (to do, see claims.md).
- Findings come mostly from one analyzer; Bandit's own findings replicate the key
  results for Python.
- Ports, not the tools: each checked against the original (Section III), but SonarQube's
  file move detection is modelled only for pairs git already detects as renames.
- Bandit's scheme applied to CodeGuard findings fills Bandit's fields with CodeGuard's
  closest equivalents; its primary result is on Bandit's own findings.
- Consecutive commits are an easy case; real baselines span many commits (drift mode
  exists but is not part of this paper).
- Web applications in Python and JavaScript/TypeScript only.

## VIII. Related work

Candidates (verify each before citing; see claims.md for what to cite them for):

- Spacco, Hovemeyer and Pugh, "Tracking defect warnings across versions", MSR 2006.
- Avgustinov et al., "Tracking static analysis violations over time to capture developer
  characteristics", ICSE 2015.
- Kim and Ernst, "Which warnings should I fix first?", ESEC/FSE 2007.
- Heckman and Williams, "A systematic literature review of actionable alert
  identification techniques for automated static code analysis", IST 2011.
- Johnson et al., "Why don't software developers use static analysis tools to find
  bugs?", ICSE 2013.
- Sadowski et al., "Tricorder: Building a program analysis ecosystem", ICSE 2015, and
  "Lessons from building static analysis tools at Google", CACM 2018.
- OASIS SARIF 2.1.0 (fingerprints and `partialFingerprints`).

Still to search: recent work on warning matching or "issue tracking" across revisions
(2016 onwards), and on baseline-based CI gates.

## IX. Conclusion

Availability: harness, ports, corpus, results and scripts in the repository
(`research/finding_identity/`), Apache-2.0.

## Regenerating

The tables, figures and claim values come from the corpus results with:

```bash
python -m research.finding_identity stats research/finding_identity/results/corpus-v3 \
    --corpus research/finding_identity/corpus.csv --out research/finding_identity/paper --plot
```

(The commands for Table II, Fig. 1 and claims.md are added once the runs finish.)
