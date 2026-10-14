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

Clones go to `.repos/` and results to `results/<label>/`; both are git-ignored, as is
`tables/` (see [Statistics](#statistics)); the aggregated tables of the corpus run are
committed under `paper/`. Each result
directory holds `summary.json`, `pairs.jsonl` (one line per commit pair) and, with
`--details`, `findings.jsonl` (one line per compared finding with its true status and each
scheme's outcome, for sampling and manual checks).

Tests:

```bash
python -m pytest research/finding_identity/tests
```

`pip install -r research/finding_identity/requirements.txt` adds the optional plotting
dependency.

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
over 200 pairs for any other repository. No other repository was affected.

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

Every replay also records its totals **per rule category** (`by_category` in
`summary.json`, with the same `totals` and `collisions` blocks as the summary itself).
Scheme keys include the rule ID and the ground truth pairs findings of the same rule
only, so each category is scored on its own findings and the categories add up exactly to
the totals.

## Statistics

```bash
python -m research.finding_identity stats research/finding_identity/results \
    --corpus research/finding_identity/corpus.csv --out research/finding_identity/tables --plot
```

For each scope (`all` findings and `security` findings by default; `--scopes` takes any
rule categories), each scheme and each metric (`false_new`, `false_new_moved`,
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

`paper/` holds the aggregated outputs of the corpus run of 2026-10-14 (CodeGuard 2.2.0,
200 commit pairs per repository, all rule categories), produced with:

```bash
python -m research.finding_identity batch research/finding_identity/corpus.csv --commits 200 --jobs 4
python -m research.finding_identity stats research/finding_identity/results \
    --corpus research/finding_identity/corpus.csv --out research/finding_identity/paper --plot
```

The batch took 14 min 44 s of wall-clock time for the 35 repositories on 4 cores
(2,781 s summed over repositories, fetching included): 7,000 commit pairs, 34,275 file
versions scanned, 36,232 findings, 8,703 of them security findings. Clones and per-commit
results are not committed.

## Known limitations

- The ground truth is a line diff. A finding whose anchor line is rewritten beyond the
  similarity threshold counts as removed plus introduced; check a sample by hand.
- CodeGuard's fingerprint takes the statement from `str.splitlines()`, which also splits on
  form feeds and other rare separators, so in files containing them the `codeguard` key can
  hash a neighbouring line. The harness measures the tool as it is.
- Taint findings depend on several lines; the ground truth tracks only the reported line.
- Every scheme's key includes the file path, so a renamed or moved file makes every
  scheme report its findings as new, even on unchanged lines. In the corpus run this is
  most of the residual false-new rate of the text-based schemes (for example Ghost, which
  renamed many `.js` files to `.ts`).
