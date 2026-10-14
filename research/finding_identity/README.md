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

## Controlled transformation experiment (RQ2)

Real histories rarely edit the flagged line itself and introduce few new findings, so
they cannot say *which kinds of change break which schemes*. The `transform` subcommand
answers that with a controlled experiment: it samples Python files with findings,
rewrites each one with a set of transformations whose effect on line identity is known
by construction, scans before and after, and scores every scheme.

| Transformation | What it does | Behaviour |
|---|---|---|
| `reformat` | `black` at line length 79 (`--reformat-line-length`; `ruff format` if black is missing) | kept |
| `insert_top` | a comment and an unused import below the docstring and `__future__` imports | kept |
| `insert_below` | a comment line right below the flagged statement (GitHub's hash reads 100 non-whitespace characters forward) | kept |
| `rename_local` | renames a local variable (not a parameter) used on the flagged line, in its whole function | kept |
| `rename_function` | renames the enclosing function or method and its references in the file (`self.m`, `cls.m`, `Class.m` for methods) | kept in the file |
| `move_function` | swaps the enclosing function with the adjacent function in the same body | kept |
| `change_literal` | appends `_v2` to a string literal on the flagged line, or adds one to a number | changed |
| `extract_helper` | moves the flagged statement into a new module-level function; reads become parameters, assignments are returned | kept |
| `duplicate_above` / `duplicate_below` | copies the flagged statement directly above / below itself: a genuinely new finding | changed |
| `ai_refactor` | asks a language model to refactor the enclosing function without changing its behaviour (optional) | checked by hand |

Each transformation returns the new text and an exact old-line to new-line map, which
is the ground truth. `reformat` pairs the syntax trees before and after (black keeps the
tree), so when it splits a line the finding is followed to the line its node starts on.
`ai_refactor` is the exception: its ground truth is the line diff of `linemap.py`, so
its cases are flagged `needs_review` and written to `review.jsonl` with the old and new
function for a manual check.

Renames, extraction and moves are rewritten with `libcst` (source preserving) and only
where they are safe within the file: names bound once, no `global`/`nonlocal`/`locals()`,
no special methods, no overridden method names, no statements that `yield`, `await` or
use `super()`. When a transformation does not fit a target finding it tries the next
finding in the file (in a seeded random order); if none fits, the file counts as "n/a"
for that transformation, with the reason. Other modules are not updated by renames.

### Running it

```bash
pip install -r research/finding_identity/requirements.txt

python -m research.finding_identity transform https://github.com/pallets/flask --samples 200 --heatmap
python -m research.finding_identity transform https://github.com/DefectDojo/django-DefectDojo \
    --ref dev --label defectdojo --samples 200 --heatmap

# A subset of transformations, on a local directory
python -m research.finding_identity transform path/to/src --transforms rename_local,extract_helper
```

`--samples` is the number of files with findings to use; `--seed` fixes the sample and
the target findings. Results go to `results/transform-<label>/` (git-ignored):

- `matrix.csv`: one row per transformation and scheme (the invariance matrix);
- `matrix.md`: the same as a Markdown table (false-new % / hidden %);
- `matrix.png`: heatmaps of the false-new and hidden rates (`--heatmap`, needs matplotlib);
- `cases.jsonl`: one line per applied transformation, with the target, its outcome under
  each scheme and the introduced findings;
- `summary.json`: all counts, including "n/a" reasons and findings lost by the change.

### Invariance matrix

Two scopes are reported. The **target** scope is the paper's matrix: per transformation,

- **false-new rate** = target findings a scheme reports as new / target findings still
  detected after the change (`target_known`);
- **hidden rate** = introduced findings a scheme matches to an old finding / introduced
  findings (only the `duplicate` transformations introduce findings);
- **mispair rate** = target findings matched to the wrong old finding / `target_known`;
- **collision rate** = findings sharing a key with another finding in the transformed file.

The **file** scope (`file_*` columns) scores every finding in the transformed file, as
a CI baseline would see the change.

A target finding that the change makes undetectable is counted as `target_lost` (with
its rule in `summary.json`) and the next finding in the file is tried; lost cases are
not scheme failures and do not enter the matrix. `extract_helper` loses most loop rules
this way (`CG-PERF-002`, `CG-PERF-005`): outside its loop the statement is no longer a
finding.

The duplicate transformations show how matching order matters: schemes pair equal keys
in line order, so a copy *above* the finding is matched to the old finding (hidden) and
the original is reported as new; GitHub's hash, which reads forward, is fooled by a copy
*below* instead.

### Optional AI refactor

`ai_refactor` uses the Anthropic API (`pip install anthropic`). No model is hard-coded:

```bash
export ANTHROPIC_API_KEY=...                 # or --ai-api-key
export FINDING_IDENTITY_AI_MODEL=<model id>  # or --ai-model
python -m research.finding_identity transform <repo> --transforms all --samples 50
```

`--transforms all` includes `ai_refactor` only when a model is set. Every reply is
cached in `.cache/ai/` (git-ignored) under a hash of the model and prompt, so a rerun
with the same cache reproduces the edits; `--ai-offline` uses the cache only. Replies
that do not parse or that rename the function count as "n/a".

## Known limitations

- The ground truth is a line diff. A finding whose anchor line is rewritten beyond the
  similarity threshold counts as removed plus introduced; check a sample by hand.
- CodeGuard's fingerprint takes the statement from `str.splitlines()`, which also splits on
  form feeds and other rare separators, so in files containing them the `codeguard` key can
  hash a neighbouring line. The harness measures the tool as it is.
- Taint findings depend on several lines; the ground truth tracks only the reported line.
- The transformations are applied one at a time to one finding each; real commits mix
  them. `change_literal` and the `duplicate` transformations change behaviour on purpose.
