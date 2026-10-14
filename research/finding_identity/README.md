# Finding identity: replay harness

Research code for the study *How well do static-analysis findings keep their identity as
code changes?* It is not part of the released `codeguard` package.

Baselines, suppressions, "fail only on new findings" CI checks and alert de-duplication all
rely on recognising that a finding in version *n+1* of a file is the same finding as one in
version *n*. This harness replays real git histories, scans every changed file before and
after each commit with an analyzer (CodeGuard, Bandit or Semgrep), and scores several
**identity schemes** against a **ground truth** built from the diff.

## Schemes

Every scheme includes the rule ID and the file path. The schemes of shipped tools are
ports of their source code at a pinned version, checked against the original tool (see
[Fidelity](#fidelity)); the docstrings cite the files and functions they port.

| Scheme | Identity is built from | Ported from |
|---|---|---|
| `line` | the line number | |
| `line_text` | the exact text of the flagged line | |
| `github` | GitHub code scanning's `primaryLocationLineHash`: a rolling hash over the 100 non-blank characters from the start of the line, plus an occurrence count | github/codeql-action `src/fingerprints.ts` |
| `sonar` | SonarQube's issue tracker, a **multi-pass matcher**: (1) same rule, line, line hash and message; (2) same rule, line and line hash; (3) code moves, by unique 11-line block hashes and then by the longest identical block; (4) same rule, line hash and message; (5) same rule, line and message; (6) same rule and line hash. The line hash is the MD5 of the line without spaces and tabs | SonarQube 26.10.0.133078, `sonar-core` `issue/tracking/Tracker.java`, `AbstractTracker.java`, `BlockRecognizer.java`, `BlockHashSequence.java`, `hash/SourceLineHashesComputer.java` |
| `bandit` | `bandit -b baseline.json`: a result is known when an issue with the same text, severity, CWE, confidence, file, test name and test ID is in the baseline. No location at all, and **set membership**: once one such issue is baselined, any number of equal new ones are hidden | Bandit 1.9.4 `bandit/core/manager.py` (`_compare_baseline_results`), `bandit/core/issue.py` (`Issue.__eq__`) |
| `semgrep` | Semgrep's `match_based_id` (JSON `extra.fingerprint`, SARIF `fingerprints["matchBasedId/v1"]`): BLAKE2b of the rule's patterns with metavariables replaced by the code they bound, the path and the rule ID, plus an ordinal among equal keys in the file. No line, column or matched code beyond the bindings. **Semgrep findings only** | Semgrep 1.180.0 `semgrep/rule_match.py` (`get_match_based_key`, `get_match_based_id`, `RuleMatches.add`), `semgrep/rule.py` (`formula_string`) |
| `codeguard` | CodeGuard's `codeguard/v1` fingerprint: enclosing function/class plus the normalized statement (literals masked, comments and whitespace removed) | `src/codeguard/engine/fingerprint.py` |
| `cg_no_scope` | ablation: `codeguard` without the enclosing scope | |
| `cg_no_mask` | ablation: `codeguard` without masking literals | |
| `cg_raw` | ablation: `codeguard` without any normalization (scope plus raw line) | |

`sonar` and `bandit` match with an algorithm rather than a key (`trackers.py`, plugged in
through `trackers.MATCHERS`); their keys hold what that algorithm compares and are used
only for the collision rate (`sonar`: rule and line hash). Bandit pairs nothing, so to
score mispairs the `bandit` matcher pairs equal issues in line order and sends surplus
new issues to the last equal old one.

Where a port fixes what the tool leaves to its environment:

- **SonarQube.** Every issue of the previous analysis gets the same update date, so a pass
  with several candidates takes the first in report order (the Java sort is stable).
  Issues reach the tracker in the analyzer's report order. Line hashes cover whole lines,
  as SonarQube computes them for external issues on files without "significant code"
  ranges; a SonarQube language plugin that reports such ranges hashes only those. Only
  the tracking of open issues runs (there are no closed issues to reopen between two
  consecutive versions). The tie-breaking order of `BlockRecognizer`, which iterates
  `java.util.HashMap` key sets, is reproduced exactly by a port of `HashMap`.
- **Bandit.** Findings from other analyzers fill Bandit's fields with their closest
  equivalents: CodeGuard's description, severity, confidence, CWE and rule title;
  Semgrep's message, severity and the rule's `confidence` and `cwe` metadata.
- **Semgrep.** Needs the rule formula and metavariable bindings, so it applies only to
  `--analyzer semgrep`.

Not included: Snyk Code's matching is closed source; reviewdog filters findings by the
diff's added lines rather than carrying identity across versions; the SARIF SDK's
multi-tool result matcher is not used by any of the analyzers here.

## Analyzers

`--analyzer` chooses what produces the findings; every analyzer is scored with all the
schemes it supports (all of the above, plus `semgrep` for Semgrep).

| Analyzer | Languages | Runs |
|---|---|---|
| `codeguard` (default) | Python, JavaScript, TypeScript | CodeGuard's rules in the `--categories` |
| `bandit` | Python | Bandit 1.9.4 with its default plugins, in process (the code path of the command line) |
| `semgrep` | Python, JavaScript, TypeScript | Semgrep 1.180.0 with the local rules in `semgrep_rules.yml` (or `--semgrep-rules`), one file at a time, offline |

Bandit and Semgrep are research-only dependencies:

```bash
pip install -r research/finding_identity/requirements.txt
```

Semgrep redacts `match_based_id` and metavariable bindings unless an app token is set.
The harness passes a placeholder token and points every proxy variable at a closed local
port, so the scan cannot reach the network. The `semgrep` key is the ID Semgrep itself
emitted; every file also checks the port against it, and `analyzer.json` in the results
records the count (`port_checked`, `port_mismatches`).

## Ground truth

For each changed file, old lines are mapped to new lines with a line diff
(`linemap.py`). Unchanged lines map exactly ("moved"). Inside a replaced block, lines are
paired when their similarity is at least 0.6 ("edited"). An old and a new finding are the
same finding when they have the same rule and the old line maps to the new line. Each new
finding is then truly **known** (it existed before) or truly **new**.

## Outcomes and metrics

For each new finding, a scheme either matches it to an old finding or not:

| Outcome | Truth | Scheme | Meaning |
|---|---|---|---|
| `known_ok` | known | matched to the right finding | correct |
| `mispaired` | known | matched to a different old finding | wrong history carried over |
| `false_new` | known | not matched | old problem reported as new: noise, broken baselines |
| `false_known` | new | matched to an old finding | **new problem hidden** |
| `new_ok` | new | not matched | correct |

The summary reports, per scheme:

- **false-new rate** = `false_new / known`, also split by moved and edited findings
- **hidden rate** = `false_known / introduced`
- **mispair rate** = `mispaired / known`
- **collision rate** = findings sharing a key with another finding in the same file version,
  over all findings in all scanned versions

Only files that changed in a commit are compared. Every scheme trivially keeps the findings
in untouched files, so including them would only inflate the counts.

## Usage

From the repository root, with CodeGuard installed (`pip install -e .`):

```bash
# Replay the last 200 first-parent commits of a repository (clones shallowly if a URL)
python -m research.finding_identity replay https://github.com/pallets/flask --commits 200

# Branch, label, rule categories, and one record per finding for manual labelling
python -m research.finding_identity replay https://github.com/DefectDojo/django-DefectDojo \
    --ref dev --commits 200 --label defectdojo --categories security,performance,quality --details

# The same history with Bandit or Semgrep findings (results go to results/flask-bandit, ...)
python -m research.finding_identity replay https://github.com/pallets/flask --commits 200 --analyzer bandit
python -m research.finding_identity replay https://github.com/pallets/flask --commits 200 --analyzer semgrep

# Rate tables for one or more runs; pools all runs into an "ALL" table
python -m research.finding_identity summarize research/finding_identity/results/* --csv rates.csv
```

Clones go to `.repos/` and results to `results/<label>/`; both are git-ignored. The label
defaults to the repository name, with `-bandit` or `-semgrep` appended for those
analyzers. Each result directory holds `summary.json`, `analyzer.json` (analyzer, version
and configuration), `pairs.jsonl` (one line per commit pair) and, with `--details`,
`findings.jsonl` (one line per compared finding with its true status and each scheme's
outcome, for sampling and manual checks).

Tests:

```bash
python -m pytest research/finding_identity/tests
```

## Fidelity

Each port is checked against the original tool, as the `github` port was against
`fingerprints.ts`. The tests run from recorded fixtures without the tools; the live tests
run when Bandit and Semgrep are installed and skip otherwise.

- **SonarQube** (`fidelity/sonar/`). `build.sh` fetches the tracker sources at the pinned
  tag and the dependency jars that tag declares (checked by SHA-256), and compiles them
  unmodified with `SonarTrackerHarness.java`, which runs `Tracker.trackNonClosed` on cases
  read from stdin. `sonar_cases.py` generates seeded cases (shifted, moved, duplicated and
  rewritten code, changed messages, many issues per file) and compares the port with
  SonarQube on each; it also compares the `HashMap` port's key order with Guava's
  `ArrayListMultimap`, including treeified buckets and removals. `--write` records the
  answers in `tests/fixtures/sonar_tracker.json`.

  ```bash
  bash research/finding_identity/fidelity/sonar/build.sh   # needs git, curl, a JDK
  python -m research.finding_identity.fidelity.sonar_cases --count 5000 --seed 1
  ```
- **Semgrep** (`fidelity/semgrep_cases.py`). Scans whole directories with
  `semgrep_rules.yml` and compares every emitted `match_based_id` with the port; `--write`
  records the inputs and IDs in `tests/fixtures/semgrep_match_based_id.json`. A live test
  also checks that SARIF carries the same IDs as JSON. The fixture holds the rules it was
  made with, so editing `semgrep_rules.yml` does not invalidate it.

  ```bash
  python -m research.finding_identity.fidelity.semgrep_cases .repos/flask .repos/django-DefectDojo
  ```
- **Bandit** (`tests/test_tools.py`). Runs `bandit` on a version, then `bandit -b` with that
  report on the next version, and asserts that the port flags exactly the issues Bandit
  reports as new, and that the in-process analyzer reports what the command line reports.

## Known limitations

- The ground truth is a line diff. A finding whose anchor line is rewritten beyond the
  similarity threshold counts as removed plus introduced; check a sample by hand.
- CodeGuard's fingerprint takes the statement from `str.splitlines()`, which also splits on
  form feeds and other rare separators, so in files containing them the `codeguard` key can
  hash a neighbouring line. The harness measures the tool as it is.
- Taint findings depend on several lines; the ground truth tracks only the reported line.
- The Semgrep analyzer runs the command line once per file version (about a second each),
  so long histories take a while. It runs the study's own rules, not the Semgrep Registry.
