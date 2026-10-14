# Finding identity: replay harness

Research code for the study *How well do static-analysis findings keep their identity as
code changes?* It is not part of the released `codeguard` package.

Baselines, suppressions, "fail only on new findings" CI checks and alert de-duplication all
rely on recognising that a finding in version *n+1* of a file is the same finding as one in
version *n*. This harness replays real git histories, scans every changed file before and
after each commit with CodeGuard, and scores several **identity schemes** against a
**ground truth** built from the diff.

## Schemes

Every key includes the rule ID and the file path.

| Scheme | Identity is built from |
|---|---|
| `line` | the line number |
| `line_text` | the exact text of the flagged line |
| `github` | GitHub code scanning's `primaryLocationLineHash` (exact port of `fingerprints.ts` from github/codeql-action, verified against the original) |
| `codeguard` | CodeGuard's `codeguard/v1` fingerprint: enclosing function/class plus the normalized statement (literals masked, comments and whitespace removed) |
| `cg_no_scope` | ablation: `codeguard` without the enclosing scope |
| `cg_no_mask` | ablation: `codeguard` without masking literals |
| `cg_raw` | ablation: `codeguard` without any normalization (scope plus raw line) |

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

# Rate tables for one or more runs; pools all runs into an "ALL" table
python -m research.finding_identity summarize research/finding_identity/results/* --csv rates.csv
```

Clones go to `.repos/` and results to `results/<label>/`; both are git-ignored. Each result
directory holds `summary.json`, `pairs.jsonl` (one line per commit pair) and, with
`--details`, `findings.jsonl` (one line per compared finding with its true status and each
scheme's outcome, for sampling and manual checks).

Tests:

```bash
python -m pytest research/finding_identity/tests
```

## Known limitations

- The ground truth is a line diff. A finding whose anchor line is rewritten beyond the
  similarity threshold counts as removed plus introduced; check a sample by hand.
- CodeGuard's fingerprint takes the statement from `str.splitlines()`, which also splits on
  form feeds and other rare separators, so in files containing them the `codeguard` key can
  hash a neighbouring line. The harness measures the tool as it is.
- Taint findings depend on several lines; the ground truth tracks only the reported line.
