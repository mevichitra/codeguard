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

## Long spans (drift mode)

Consecutive commits are an easy test: in the pilot (Flask, 100 commits; DefectDojo, 200
commits) 690 of 695 persisting findings had only moved, and every content-based scheme
lost 0-1.4% of them. Real baselines are created once and compared with much later
versions, so `drift` measures long spans. It picks an **anchor** commit c0, `--anchor-back`
first-parent commits behind `--ref`, and compares c0 with c_k, the k-th first-parent
commit after it, for each span k in `--spans`. Outcomes and metrics are the same as above,
reported per span.

**Chained ground truth.** A direct c0 -> c_k diff mis-maps code that moved and loses lines
that were rewritten a little at a time. Instead, each anchor finding's line is followed
through every intermediate first-parent commit: for each step whose diff touches the
file it is in, the line is mapped with the same line diff as above (`linemap.map_lines`),
and renames are followed per step (`git diff -M`). A finding persists to c_k when its
chain is unbroken (file not deleted, line mapped at every step) and a finding with the
same rule sits at the mapped line in c_k. It counts as **edited** when any step mapped
its line as edited, otherwise as **moved**.

**What is compared.** For span k: the files of c0 whose lineage changed in steps 1..k,
the files they became at c_k, and the files added since c0. Files never touched in the
span are left out, as in the consecutive mode. Keys always use the file's own path at
each end, so a renamed file loses its findings under every scheme; the ground truth
still counts them as persisting, which is the point.

**Cost.** Only c0 and each c_k are scanned. Intermediate commits are read only as blob
contents of files that hold tracked findings (through `git cat-file --batch`), to compute
the line maps.

Each drift result directory holds `summary.json` (one entry per span, with the same
`totals` and `collisions` as a replay summary plus `chains`: anchor findings tracked,
chains still alive at c_k, and how many of those were edited) and, with `--details`,
`findings.jsonl` (one record per finding at c_k, with its span, path, the anchor path of
its true predecessor and each scheme's outcome).

## Usage

From the repository root, with CodeGuard installed (`pip install -e .`):

```bash
# Replay the last 200 first-parent commits of a repository (clones shallowly if a URL)
python -m research.finding_identity replay https://github.com/pallets/flask --commits 200

# Branch, label, rule categories, and one record per finding for manual labelling
python -m research.finding_identity replay https://github.com/DefectDojo/django-DefectDojo \
    --ref dev --commits 200 --label defectdojo --categories security,performance,quality --details

# Rate tables for one or more runs; pools all runs into an "ALL" table
python -m research.finding_identity summarize research/finding_identity/results/flask \
    research/finding_identity/results/django-DefectDojo --csv rates.csv

# Long spans: anchor 200 first-parent commits back, compare it with 1, 10, 50, 100, 200
python -m research.finding_identity drift https://github.com/pallets/flask \
    --anchor-back 200 --spans 1,10,50,100,200
python -m research.finding_identity drift https://github.com/DefectDojo/django-DefectDojo \
    --ref dev --anchor-back 200 --spans 1,10,50,100,200 --details

# One table per span and scheme x span pivots; the CSV has one row per run, span and
# scheme (pooled "ALL" rows too), ready to plot false-new and hidden rate against span
python -m research.finding_identity drift-summary research/finding_identity/results/drift/* \
    --csv drift.csv
```

Clones go to `.repos/` and results to `results/<label>/` (drift: `results/drift/<label>/`);
both are git-ignored. Each result
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

Drift mode adds its own limits:

- One anchor per run, so a span's numbers come from one pair of commits. Short spans in
  particular are small samples; use several anchors (`--ref` at different commits) to
  get variance.
- A chain breaks for good at any step that rewrites the line beyond the threshold,
  deletes the file, or moves the code to another file (git sees a deletion plus an
  addition, not a move). The finding then counts as removed and its successor as
  introduced, which can only make a scheme look like it *hides* a new finding when it in
  fact kept an old one. A file deleted and later re-added at the same path also starts a
  new lineage. Sample `false_known` records by hand.
- Within one step, a block that moved past other changed lines is not followed: the line
  diff sees a deletion plus an insertion. Chaining limits this to the commit that did the
  move, instead of every later span.
- Renames are those `git diff -M` detects between consecutive commits (50% similarity by
  default); copies are not followed.
- Shallow clones must reach the anchor: clones are made with depth `--anchor-back + 2`,
  and an existing clone that is too shallow is reported, not deepened.
