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
| `sonar_branch` | the `sonar` tracker as a **branch analysis** runs it. A renamed file keeps its findings only if SonarQube's file move detection takes it for the old file: line counts within (0.84×, 1.18×) and a similarity of at least 85, where similarity is 100 × (1 − edit distance / longer length) over the line hashes. `sonar` is the **pull-request** analysis, which takes renames from the SCM | SonarQube 26.10.0.133078, `sonar-ce-task-projectanalysis` `filemove/FileMoveDetectionStep.java`, `SourceSimilarityImpl.java` |
| `bandit` | `bandit -b baseline.json`: a result is known when an issue with the same text, severity, CWE, confidence, file, test name and test ID is in the baseline. No location at all, and **set membership**: once one such issue is baselined, any number of equal new ones are hidden | Bandit 1.9.4 `bandit/core/manager.py` (`_compare_baseline_results`), `bandit/core/issue.py` (`Issue.__eq__`) |
| `semgrep` | Semgrep's `match_based_id` (JSON `extra.fingerprint`, SARIF `fingerprints["matchBasedId/v1"]`): BLAKE2b of the rule's patterns with metavariables replaced by the code they bound, the path and the rule ID, plus an ordinal among equal keys in the file. No line, column or matched code beyond the bindings. **Semgrep findings only** | Semgrep 1.180.0 `semgrep/rule_match.py` (`get_match_based_key`, `get_match_based_id`, `RuleMatches.add`), `semgrep/rule.py` (`formula_string`) |
| `codeguard` | CodeGuard's `codeguard/v1` fingerprint: enclosing function/class plus the normalized statement (literals masked, comments and whitespace removed) | `src/codeguard/engine/fingerprint.py` |
| `cg_no_scope` | ablation: `codeguard` without the enclosing scope | |
| `cg_no_mask` | ablation: `codeguard` without masking literals | |
| `cg_raw` | ablation: `codeguard` without any normalization (scope plus raw line) | |

`sonar`, `sonar_branch` and `bandit` match with an algorithm rather than a key
(`trackers.py`, plugged in through `trackers.MATCHERS`); their keys hold what that
algorithm compares and are used only for the collision rate (`sonar` and `sonar_branch`:
rule and line hash). Bandit pairs nothing, so to
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
  `java.util.HashMap` key sets, is reproduced exactly by a port of `HashMap`. For
  `sonar_branch`, the file move detection scores every removed file against every added
  file and elects the best pairs; the harness already pairs files by git's rename
  detection (`git diff -M`, 50% similarity), so only SonarQube's decision for that pair
  is ported. A move SonarQube would find but git would not is therefore not modelled.
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
| `semgrep` | Python, JavaScript, TypeScript | Semgrep 1.180.0, offline, with the rules in `semgrep_rules.yml` or `--semgrep-rules` (a rules file or a rules repository, below) |

Bandit and Semgrep are research-only dependencies:

```bash
pip install -r research/finding_identity/requirements.txt
```

### Semgrep's rules

`semgrep_rules.yml` was written for this study. For findings that do not come from rules
the study chose, `--semgrep-rules` also takes a checkout of a rules repository in the
layout of [semgrep/semgrep-rules](https://github.com/semgrep/semgrep-rules), one directory
per language. Python files are scanned with `python/`, JavaScript and TypeScript files
with `javascript/` and `typescript/`; the other directories (`generic/`, ...) are left
out. The rules are copied into the scan directory, so Semgrep's rule IDs (and so
`match_based_id`) do not depend on where the checkout lives; the harness records the IDs
without the copy's prefix (`python.lang.security.audit.eval-detected`). `analyzer.json`
records the checkout's commit, a SHA-256 over the rule files, and the number of rules.

The paper uses [opengrep/opengrep-rules](https://github.com/opengrep/opengrep-rules) at
`f1d2b562b414783763fd02a6ed2736eaed622efa` (2025-01-26): the semgrep-rules repository as it
was under LGPL-2.1 with the Commons Clause, before Semgrep, Inc. moved the rules to the
Semgrep Rules License (December 2024), which limits use to internal purposes and does not
allow redistribution. The fork's licence allows research use and redistribution, but not
selling the rules.

```bash
git clone https://github.com/opengrep/opengrep-rules research/finding_identity/.repos/opengrep-rules
git -C research/finding_identity/.repos/opengrep-rules checkout f1d2b562b414783763fd02a6ed2736eaed622efa
```

Loading a rules repository takes Semgrep 10 to 30 seconds, so a replay does not scan one
file version per call. Before the first commit pair it collects every file version the
replay will scan and hands them to `SemgrepAnalyzer.prefetch`, which scans them in
layers: a layer holds one kind of file (Python, or JavaScript and TypeScript) and at most
one version of each path, so each file is scanned at its own path with the rules it would
get alone. A repository needs as many calls as its most-changed file has versions (5 to
34 in the corpus) for each kind of file. A test checks that the layered results equal
one-file-at-a-time results; `analyzer.json` records the number of calls
(`semgrep_calls`), the versions prefetched, any layer that failed (its files are then
scanned one at a time) and the errors Semgrep reported, by type (`scan_errors`).

Semgrep redacts `match_based_id` and metavariable bindings unless an app token is set.
The harness passes a placeholder token and points every proxy variable at a closed local
port, so the scan cannot reach the network. The `semgrep` key is the ID Semgrep itself
emitted; every file also checks the port against it, and `analyzer.json` in the results
records the count (`port_checked`, `port_mismatches`).

## Ground truth

For each changed file, old lines are mapped to new lines (`linemap.py`) in three steps:

1. **Unchanged** lines, as a line diff (`difflib`) keeps them, map exactly (`equal`).
2. Inside a replaced block, lines are paired when their similarity (difflib's `ratio`) is
   at least 0.6, by an order-preserving alignment that maximizes total similarity
   (`edited`). Blocks up to 40,000 old x new lines get the full alignment; larger ones are
   aligned inside a band around the block's diagonal, and the replay counts the findings
   in such blocks (`known_banded`, `introduced_banded`).
3. **Moved code** (`relocated`): a block of consecutive lines the diff left unmapped that
   reappears, line for line, as a block of consecutive unmapped new lines. Modelled on
   `git diff --color-moved=blocks` (a moved block has at least 20 alphanumeric
   characters), except that lines are compared without leading and trailing whitespace
   (a re-indented block still counts as moved) and that a block is mapped only when its
   text occurs exactly once in the old version and once in the new one (copies of
   repeated code are never paired by guess).
   An edit inside a moved block splits it in two; the lines between two such halves (at
   most 10 on either side) are aligned as in step 2 and count as `edited`.

An old and a new finding are the same finding when they have the same rule and the old
line maps to the new line. Each new finding is then truly **known** (it existed before)
or truly **new**. Moves between files are not detected.

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

- **false-new rate** = `false_new / known`, also split by the kind of the finding's
  line mapping: unchanged, edited and relocated
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
its line as edited, otherwise as **moved**. A file deleted and later added again at the
same path (a revert) resumes its chains, through the line map from the deleted version to
the re-added one, so that a baseline seeing the same file at both ends is not charged with
hiding its findings; `summary.json` counts these as `readded_files`. Only c0 and c_k
matter for the rule itself: a finding not reported at some intermediate commit but
reported again at c_k, on the line its chain leads to, persists.

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

# The same history with Bandit or Semgrep findings (results go to results/flask-bandit, ...)
python -m research.finding_identity replay https://github.com/pallets/flask --commits 200 --analyzer bandit
python -m research.finding_identity replay https://github.com/pallets/flask --commits 200 --analyzer semgrep

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

# The whole corpus, three anchors per repository (200, 300 and 400 first-parent commits
# behind the pin, each followed for 200 commits), pooled per repository and reported with
# cluster-bootstrap intervals: see drift_kit.py and paper/outline.md ("Regenerating")
python -m research.finding_identity.drift_kit fetch
python -m research.finding_identity.drift_kit run --out research/finding_identity/results/drift-v1
python -m research.finding_identity.drift_kit report research/finding_identity/results/drift-v1
```

Clones go to `.repos/` and results to `results/<label>/` (drift: `results/drift/<label>/`);
both are git-ignored, as is `tables/` (see [Statistics](#statistics)); the aggregated
tables of the corpus run are committed under `paper/`. The label defaults to the
repository name, with `-bandit` or `-semgrep` appended for those analyzers. Each result
directory holds `summary.json`, `analyzer.json` (analyzer, version and configuration),
`pairs.jsonl` (one line per commit pair) and, with `--details`, `findings.jsonl` (one
line per compared finding with its true status and each scheme's outcome, for sampling
and manual checks).

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

# A pinned commit of a corpus clone (clones made by `batch` have no working tree)
python -m research.finding_identity transform research/finding_identity/.repos/zulip \
    --ref <pinned sha> --label zulip --samples 40
```

With a local repository and `--ref`, the Python files of that commit are exported to a
temporary directory and `summary.json` records the commit as `head`.

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

## Corpus

`corpus.csv` lists the repositories of the study, each pinned to one commit. Columns:
`label`, `url`, `branch`, `sha` (the pinned commit), `pinned` (date of pinning),
`language` (backend language: `python`, or `javascript` for JavaScript/TypeScript),
`framework`, `license` (SPDX), `rationale` (why it qualifies and where its
security-relevant code is), and four columns measured at the pinned commit by
`corpus check`: `commit_date`, `commits_2y`, `py_files`, `js_files`.

### Selection criteria

A repository is in the corpus when all of these hold:

1. **Kind.** A deployable web *application* (or an application server distributed as a
   package), not a library, framework, SDK, tutorial, template, sample or intentionally
   vulnerable training project; and not a fork. Judged by hand from the project's own
   description; the `rationale` column records it.
2. **Language.** A Python back end (Flask, Django, FastAPI, or another Python web
   framework: Pyramid, web.py, Frappe) or a JavaScript/TypeScript back end (Express,
   Koa, Fastify, NestJS, Next.js API routes). The back-end language must have at least
   100 source files that the harness analyses (vendored, generated and minified files
   excluded) and more of them than the other language, so that every repository counts
   cleanly as a Python or a JavaScript/TypeScript project.
3. **Security-relevant code.** Handles HTTP requests from users and does at least one of:
   builds SQL or other database queries, renders templates, runs subprocesses, accepts
   file uploads, fetches user-supplied URLs, or implements authentication. Recorded in
   `rationale`.
4. **History.** At least 200 first-parent commits on the pinned branch in the 730 days
   before the pinned commit (the replay needs 200 commit pairs; this also shows
   sustained activity).
5. **Activity.** The pinned commit is at most 90 days older than the pinning date.
6. **Licence.** The root licence file (`LICENSE`, `LICENCE` or `COPYING`) is one
   OSI-approved licence (MIT, BSD-2/3-Clause, Apache-2.0, MPL-2.0, GPL-2.0/3.0,
   AGPL-3.0, LGPL, PostgreSQL) for the whole repository. Source-available licences
   (Business Source, Sustainable Use, Functional Source, Elastic, Commons Clause) and
   root licences that put some directories under other terms (typically an `ee/`
   enterprise edition) are excluded, because the replay scans every directory.
7. **No committed build output.** The repository does not track bundler output (minified,
   content-hashed JavaScript) outside the paths the harness already skips (`dist/`,
   `build/`, `node_modules/`, `*.min.js`, ...). Such files are rewritten wholesale by every
   build and would swamp the real code's findings.
8. **Branch.** The default branch, unless the project develops on another branch
   (DefectDojo's `dev`, IntelOwl's `develop`: their default branches only receive
   releases); the branch is recorded.

Criteria 1, 3 and 7 are judged by hand. The file counts of criterion 2 and criteria 4, 5
and 6 are measured from git alone at the pinned commit, so anyone can re-check them later
with the same result:

```bash
python -m research.finding_identity corpus check research/finding_identity/corpus.csv
```

`corpus pin` re-pins every row (or `--only a,b`) to the current head of its branch; that
is how the corpus was built, from a candidate list of 60 repositories on 2026-10-14. The
35 that met every criterion (25 Python, 10 JavaScript/TypeScript) form the corpus; the 25
that failed a criterion were dropped (reasons as `corpus check` reported them; "mixed"
means the root licence puts some directories under other terms). Criterion 7 was added
during the first batch run, when CTFd turned out to commit its Vite build output: its
replay compared 12,944 findings in its first 75 commit pairs, against at most about 4,000
over 200 pairs for any other repository. No other repository was affected. Its finished
replay (200 pairs, 28 minutes) has 22,122 persisting findings, as many as the other 35
repositories together (23,237); including it would raise the pooled `codeguard`
false-new rate from 1.8% to 48.7% while the per-repository median stays at 0.5%.

| Candidate | Reason |
|---|---|
| ctfd (CTFd/CTFd) | commits Vite build output (`CTFd/themes/*/static/assets/*-<hash>.js`) that the harness does not skip (criterion 7) |
| paperless-ngx (paperless-ngx/paperless-ngx) | Python is not the majority language (410 py, 435 js) |
| mathesar (mathesar-foundation/mathesar) | pinned commit is 93 days old; Python is not the majority language (235 py, 492 js) |
| redash (getredash/redash) | only 194 first-parent commits in 730 days; Python is not the majority language (291 py, 577 js) |
| superset (apache/superset) | Python is not the majority language (2988 py, 4187 js) |
| dispatch (Netflix/dispatch) | pinned commit is 407 days old |
| polar (polarsource/polar) | Python is not the majority language (2167 py, 2473 js) |
| archery (hhyo/Archery) | only 102 first-parent commits in 730 days |
| tandoor (TandoorRecipes/recipes) | licence file reads as non-osi (commons clause), declared AGPL-3.0 |
| label-studio (HumanSignal/label-studio) | Python is not the majority language (746 py, 1951 js) |
| plane (makeplane/plane) | Python is not the majority language (671 py, 3031 js) |
| privacyidea (privacyidea/privacyidea) | Python is not the majority language (685 py, 989 js) |
| authentik (goauthentik/authentik) | licence file reads as mixed (MIT), declared MIT |
| posthog (PostHog/posthog) | licence file reads as mixed (MIT), declared MIT |
| seahub (haiwen/seahub) | Python is not the majority language (1069 py, 1592 js) |
| twenty (twentyhq/twenty) | licence file reads as mixed (AGPL-3.0), declared AGPL-3.0 |
| strapi (strapi/strapi) | licence file reads as mixed (MIT), declared MIT |
| medusa (medusajs/medusa) | licence file reads as mixed (MIT), declared MIT |
| parse-server (parse-community/parse-server) | only 83 first-parent commits in 730 days |
| umami (umami-software/umami) | only 87 first-parent commits in 730 days |
| budibase (Budibase/budibase) | licence file reads as non-osi (business source license), declared GPL-3.0 |
| rocketchat (RocketChat/Rocket.Chat) | licence file reads as mixed (MIT), declared MIT |
| infisical (Infisical/infisical) | licence file reads as mixed (MIT), declared MIT |
| dub (dubinc/dub) | licence file reads as mixed (AGPL-3.0), declared AGPL-3.0 |
| novu (novuhq/novu) | licence file reads as missing, declared MIT |

## Batch runs

```bash
# Replay every corpus repository at its pinned SHA, 4 repositories at a time
python -m research.finding_identity batch research/finding_identity/corpus.csv \
    --commits 200 --jobs 4
```

Each repository is fetched shallowly at its pinned SHA (no checkout) into `.repos/<label>`
and replayed in its own `replay` process, so a crash or a `--timeout` only affects that
repository. The batch is **resumable**: a repository whose `results/<label>/summary.json`
was produced from the pinned SHA with at least `--commits` commit pairs is skipped, so
rerunning the same command only retries failures and repositories that were not reached
(`--force` reruns everything; a changed SHA or a larger `--commits` reruns that
repository). Failures do not stop the batch: each attempt is appended to
`results/batch.jsonl` (label, status, error, seconds) and each replay's output goes to
`results/_logs/<label>.log`; the command exits with status 1 if any repository failed.
`--only a,b` restricts the run, `--delete-clones` removes each clone after its replay.

`--analyzer bandit|semgrep` replays the corpus with that analyzer's findings (see
[Analyzers](#analyzers)); results go to `results/corpus-<analyzer>/` unless `--out` is
given. Bandit reads Python only, so its batch leaves out the JavaScript repositories. A
result directory counts as done only for the analyzer named in its `analyzer.json`, so
runs of different analyzers never satisfy each other's resume check.

```bash
python -m research.finding_identity batch research/finding_identity/corpus.csv \
    --commits 200 --jobs 4 --analyzer bandit
```

Every replay also records its totals **per rule category** (`by_category` in
`summary.json`, with the same `totals` and `collisions` blocks as the summary itself).
Scheme keys include the rule ID and the ground truth pairs findings of the same rule
only, so each category is scored on its own findings and the categories add up exactly to
the totals.

## Observation cache and rescoring

A replay spends nearly all its time in the analyzer; scoring a scheme needs only the
findings and the file text. `--observations <dir>` (on `replay`, `batch`, `transform`,
`drift` and `drift_kit run`) records every scanned file version under
`<dir>/<label>/`: `versions.jsonl.gz` holds, per blob SHA and path, the scan's status
and the raw findings (rule, line, column, message and the fields Bandit compares, plus
Semgrep's emitted ID); `pairs.jsonl` holds each commit pair's changes; `meta.json` the
run and the analyzer's description. No scheme key is stored.

`rescore` replays a recording through the same code as a live replay, reading findings
from the cache and file text from the clone's git blobs, and computes the keys of any
schemes, including ones added to `schemes.py` or `trackers.py` after the run:

```bash
# Record while replaying (results as usual, the cache beside them)
python -m research.finding_identity batch research/finding_identity/corpus.csv \
    --commits 200 --jobs 4 --details --out results/corpus-v4 \
    --observations results/obs-codeguard

# Rescore every scheme and check that it reproduces the live run exactly
python -m research.finding_identity rescore results/obs-codeguard --out results/rescored \
    --check results/corpus-v4

# Iterate on one scheme: score it alone and take the others from an earlier run
python -m research.finding_identity rescore results/obs-codeguard --schemes codeguard_v2 \
    --merge-from results/corpus-v4 --out results/trial-1
```

The output has a live replay's layout, so `paper_kit`, `stats`, `gate`, `gt_agreement`
and the leaderboard read it unchanged. A full rescore takes a quarter of the live time
(SonarQube's tracker and GitHub's rolling hash are most of what is left); one scheme with
`--merge-from` takes about a tenth. `transform --from-observations` and `drift
--from-observations` replay their own recordings the same way.

`leaderboard` ranks every scheme on every RQ1 metric per analyzer (and, with
`--transform` and `--drift`, on the invariance matrix and the longest span), with each
scheme's paired difference to the best one on the same findings; `--repos <file>`
restricts it to a list of repositories, for a held-out split:

```bash
python -m research.finding_identity.leaderboard --codeguard results/corpus-v4 \
    --bandit results/corpus-bandit-v2 --semgrep results/corpus-semgrep \
    --transform results/transform --drift results/drift-v2 --out paper/leaderboard.md
```

## Statistics

```bash
python -m research.finding_identity stats research/finding_identity/results \
    --corpus research/finding_identity/corpus.csv --out research/finding_identity/tables --plot
```

For each scope (`all` findings and `security` findings by default; `--scopes` takes any
rule categories), each scheme and each metric (`false_new`, `false_new_unchanged`,
`false_new_edited`, `hidden`, `mispair`, `collision`, defined as above), `stats` reports:

- **pooled (micro) rate**: total numerator over total denominator across repositories,
  with a **Wilson 95% interval**. Wilson assumes independent findings, so it is too narrow
  for a corpus where findings in one repository are correlated;
- **cluster bootstrap 95% interval** of the pooled rate: repositories are resampled with
  replacement (10,000 resamples, fixed seed, the same resamples for every table), the
  pooled rate is recomputed, and the 2.5th and 97.5th percentiles are taken. This is the
  interval to quote;
- **macro rate**: the mean of per-repository rates, with its own cluster bootstrap
  interval. Pooled rates are dominated by the repositories with the most findings; macro
  rates weigh every repository equally;
- **median and interquartile range** of the per-repository rates (quantiles with linear
  interpolation, numpy's default).

A repository with a zero denominator for a metric (for example no persisting security
findings) has no rate: it adds nothing to the pooled sums and is left out of the macro
rate, median and quartiles; `repos_with_rate` counts the rest.

Outputs in `--out`:

| File | Contents |
|---|---|
| `pooled.csv` | one row per scope, scheme and metric: counts, pooled rate, Wilson and bootstrap intervals, macro rate and interval, median, quartiles |
| `per_repo.csv` | one row per scope, repository, scheme and metric: numerator, denominator, rate |
| `repos.csv` | one row per repository: pinned head, commit pairs, versions scanned, runtime, findings per scope |
| `tables.md` | the pooled tables in Markdown |
| `per_repo.md` | per-repository false-new rates of every scheme, per scope, in Markdown |
| `false_new_by_repo.png` | with `--plot`: box plot of per-repository false-new rates per scheme, one panel per scope (needs `matplotlib`, see `requirements.txt`) |

### Committed results

`paper/` holds the outputs the paper is written from, produced on 2026-10-17 from the
corpus pinned on 2026-10-14 (CodeGuard 2.2.0, Bandit 1.9.4, 200 commit pairs per
repository, all rule categories):

- `outline.md`: the plan of the paper; its *Regenerating* section has the exact commands
  that produce every file below;
- `claims.md`: every number the paper can cite, with its interval and source;
- `table_rq1.tex`, `numbers.md`, `rq1.csv`: RQ1 from `paper_kit.py`, including the
  false-new rate split by renamed files and Bandit's findings with and without B101;
- `fig_rq2.pdf`, `rq2.csv`: RQ2, the invariance matrix pooled over the 25 Python
  repositories (40 sampled files each);
- `tables.md`, `pooled.csv`, `per_repo.csv`, `per_repo.md`, `repos.csv`,
  `false_new_by_repo.png`: the `stats` tables for the CodeGuard replays;
- `ground_truth_check/`: a seeded sample of 100 ground-truth decisions to check by hand.

The CodeGuard batch took 18 min 20 s of wall-clock time for the 35 repositories on 4
cores, the Bandit batch 6 min 55 s for the 25 Python repositories, and the
transformation runs 7 min 41 s. Clones and per-commit results are not committed. The
replay results of the `line`, `line_text`, `github` and `codeguard` families are
identical to those of the first corpus run (2026-10-14), which had no SonarQube or
Bandit schemes.

## Known limitations

- The ground truth is a line diff with move detection. A finding whose anchor line is
  rewritten beyond the similarity threshold counts as removed plus introduced, and so does
  one whose line moved to another file, moved in a block that is not unique, or moved in
  a block with fewer than 20 alphanumeric characters; check a sample by hand.
- CodeGuard's fingerprint takes the statement from `str.splitlines()`, which also splits on
  form feeds and other rare separators, so in files containing them the `codeguard` key can
  hash a neighbouring line. The harness measures the tool as it is.
- Taint findings depend on several lines; the ground truth tracks only the reported line.
- The Semgrep analyzer runs the command line once per file version (about a second each),
  so long histories take a while. It runs the study's own rules, not the Semgrep Registry.
- The transformations are applied one at a time to one finding each; real commits mix
  them. `change_literal` and the `duplicate` transformations change behaviour on purpose.
- Every scheme's key includes the file path, so a renamed or moved file makes every
  scheme report its findings as new, even on unchanged lines. In the corpus run this is
  most of the residual false-new rate of the text-based schemes (for example Ghost, which
  renamed many `.js` files to `.ts`).

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
