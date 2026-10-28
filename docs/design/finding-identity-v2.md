# Finding identity v2: design

How CodeGuard decides that a finding in today's scan is one it has seen before, what
that gets wrong, and the scheme and matcher that replace it. The measurements come
from the finding-identity study in `research/finding_identity/` (its paper is in
`paper/`); the behaviours are pinned by `tests/test_engine/test_identity_behaviour.py`.

**Status.** Section 2 is implemented in `engine/identity.py` (the record and its
builder), `engine/matcher.py` (`match`, `MatchConfig`), `engine/filepairs.py`
(`pair_files`, `PairConfig`), `engine/baseline.py` (schema 2) and `engine/gitdiff.py`
(`head_commit`, `renames_since`); the user-facing description is `docs/identity.md`.
Where the implementation differs from the text below: the keys are `stmt`, `nscope`,
`ident`, `body`, `lh` plus the tie-break keys `ctx_prev` and `ctx_next` (two keys, so
the following line can count more than the preceding one); the identifier pass and
the similarity pass refuse to follow an identifier that still exists in the other
version's scope (`identifier_gate`), which keeps `eval(b)` beside a surviving `a` a
new finding; a pairing is *ambiguous* when a competing candidate had the same or any
context evidence, not only when the scores tied; the similarity threshold defaults to
0.7 and the token sets keep identifiers (literals masked); the passes run in the order
`stmt`, `v1`, `nscope`, `body`, `ident`, `sim`.

## 1. What ships today (`codeguard/v1`)

### The key

`codeguard.engine.fingerprint.compute` returns the first 16 hex characters of

    sha256(rule_id \0 relative_path \0 scope \0 normalized_statement)

- `relative_path`: the file's path relative to the project root (forward slashes).
  So the path is part of the identity.
- `scope`: for Python, the dotted name of the innermost enclosing function or class
  (`python_scope`, from the `ast` tree: `View.get`, `handler`, `""` at module level).
  For JavaScript and TypeScript the runner passes `scope=""` always: the tree-sitter
  backend has no scope lookup, so JS/TS findings are keyed on the statement alone.
- `normalized_statement`: the finding's *own source line* (one line, `split_lines` on
  LF, CRLF and CR only), with string literals replaced by `STR`, `#`/`//` comments
  removed, number literals replaced by `NUM`, and all whitespace removed. Nothing else
  of the statement (a multi-line call, the preceding line) takes part.

Computed in `AnalysisRunner.run` for every finding (and for the meta-findings about
suppressions). The same function is what the research harness measures as the
`codeguard` scheme (`research/finding_identity/schemes.py` calls `cg_fp.compute` and
`cg_fp.python_scope`), so the paper's numbers are the shipped code's.

Where it appears: JSON `fingerprint`, SARIF `partialFingerprints["codeguard/v1"]`, the
LSP finding payload (the VS Code extension copies it to the clipboard and uses it in
tree-item ids), and the baseline file.

### The baseline

`.codeguard-baseline.json` (schema `version: 1`) is a map from fingerprint to
`{rule_id, file, first_seen}`, plus `tool_version` and `created`.

- `baseline create`: full scan with the config applied, suppressed findings dropped,
  every remaining fingerprint stored.
- `baseline update`: adds fingerprints that are not in the file; keeps `first_seen`.
- `baseline prune`: drops entries whose fingerprint no current finding has.
- `scan --baseline` / `codeguard ci` / `[codeguard] baseline` in `codeguard.toml`:
  `apply_baseline` marks a finding `baselined` iff `f.fingerprint in baseline`.
  Baselined findings are hidden from the terminal output unless `--show-suppressed`,
  keep `"baselined": true` in JSON, get a SARIF `suppressions` entry
  (`kind: external, justification: in baseline`), are `notice`-level GitHub
  annotations and `<skipped>` in JUnit, and never affect the exit code
  (`gating_findings`). `--diff` only narrows which files are scanned; the baseline
  check is the same.

So the comparison is **set membership**: a finding is known when *any* baselined
finding ever had the same key. One entry hides any number of equal findings.

### What the study measured

On 7,000 consecutive commit pairs from 35 web applications (CodeGuard 2.2.0 findings;
`paper/claims.md` has every number with its source):

| failure | rate | cause |
|---|---|---|
| persisting finding reported as new, overall | 1.80% | |
| ... of which in renamed files | 287 of 418 (69%) | the path is in the key |
| ... same path | 0.57% | edited flagged lines (74.8% of those are lost), renamed scope |
| new finding hidden | 1.53% (30 of 1,966) | one-to-one pairing in line order with 18.6% key collisions |
| after `rename_function` / `extract_helper` | 100% new | the scope is in the key |
| after `rename_local` | 97.9% new | the identifier is in the statement |
| after `change_literal`, `insert_top`, `move_function`, `reformat` | 0%, 0%, 0%, 16.7% new | masking and no line numbers work |
| 200 commits after a baseline | 12.2% of persisting findings new | renames pile up (10.5% of findings) |

The harness pairs findings one to one; the product does not even do that. Set
membership adds the failures of the twin tests in `test_identity_behaviour.py`: a
second equal statement in the same scope is never reported, and a copy pasted above a
baselined finding is hidden.

SonarQube's tracker, the best scheme measured, keeps 0.40% / 1.12% (false new / hidden)
because it (1) keeps the path out of the key and follows SCM renames, (2) runs several
passes on different evidence (line + line hash + message, then line hash, then moved
blocks, then message), and (3) pairs one to one. Its remaining losses are renamed
functions (59% in RQ2), reformatting (17.6%) and renamed locals (9.8%): it has no
normalization at all. v2 combines both.

## 2. `codeguard/v2`: a structured identity plus a matcher

The identity of a finding is no longer one hash but a small record of keys, computed
once per finding and stored with it. A **matcher** pairs the baseline's findings with
the scan's findings one to one, trying the keys from strictest to loosest. Matching,
not hashing, is where "same finding" is decided.

### 2.1 Per-finding identity record

```json
{
  "rule": "CG-SEC-003",
  "file": "pkg/views.py",          // not part of any key; used to pair files
  "line": 42,                      // not part of any key; tie-breaking and reporting
  "scope": "View.get",
  "k": {
    "stmt":   "3e84a943de4296bc",  // sha(rule, scope, normalized statement)      = v1 minus the path
    "nscope": "b1c2...",           // sha(rule, normalized statement)             scope-free
    "ident":  "77aa...",           // sha(rule, scope, identifier-masked statement)
    "ctx":    "90de...",           // sha(rule, normalized statement, normalized previous and next non-blank lines)
    "lh":     "e4f1..."            // sha(rule, line hash: the raw line without whitespace)
  },
  "stmt_tokens": ["return", "eval", "(", "ID", ")"]  // for the similarity pass; optional
}
```

- `stmt`: the v1 payload without the path. Same normalization as today, so v1
  fingerprints can be re-derived from a v1 baseline only when the path is known
  (it is: v1 entries store `file`), which is what the migration uses.
- `nscope`: no scope, for renamed and extracted functions.
- `ident`: identifiers that are not keywords, builtins or attribute names after a dot
  are replaced by `ID`; literals masked as before. For renamed locals.
- `ctx`: the normalized statement plus the normalized previous and next non-blank
  lines. Used only to **break ties** between candidates with equal `stmt`, never as a
  pass of its own: a copy pasted above a finding has the same `stmt` but a different
  `ctx` on one side, and the original keeps the matching following context (the way
  GitHub's forward-reading hash gets `duplicate_above` right).
- `lh`: SonarQube's weakest key, for statements the normalizer cannot parse (and as a
  cheap guard against a normalizer bug reproducing itself on both sides).
- `stmt_tokens`: the tokenized statement for the similarity pass (section 2.3). Stored
  only in the baseline, never in SARIF.

JS/TS get a scope too: the enclosing `function_declaration`, `method_definition`,
`class_declaration` and arrow function assigned to a name, from the tree-sitter tree
(`LanguageSupport.scope_at(line)`, new; Python keeps `python_scope`). This alone fixes
nothing measured (the harness gave JS findings `scope=""` as well), but it lets the
tie-breaking and the `nscope` fallback mean the same thing in both languages.

The multi-line statement question: v1 hashes one source line. For a call spanning
lines the finding's line is the first, and reformatting that re-wraps the call
changes the line (RQ2 `reformat`: 16.7% new). v2 takes the statement's full span from
the parser when the finding has `end_line` (both backends provide it), normalizes the
joined text, and falls back to the single line otherwise.

### 2.2 The matcher

Input: the baseline's records grouped by file; the scan's findings grouped by file;
an optional map of renames `{old path: new path}`.

```
pair_files():
    same path                              -> paired
    renames from git (section 2.4)         -> paired
    else, removed x added files with the same extension:
        pair when >= 50% of the smaller file's `lh` keys occur in the other
        (one pass over a dict of lh -> files; greedy best score, each file once)

for each file pair, for each rule:
    old = unmatched baseline records of that rule, new = unmatched scan findings
    for key in (stmt, nscope, ident, lh):           # passes, strict to loose
        group old and new by key
        for each key with candidates on both sides:
            if one on each side: pair
            else: pair in line order, but prefer the candidate whose `ctx`
                  matches, then the nearest line; any leftover with >1
                  candidates on the other side is flagged `ambiguous`
    similarity pass (section 2.3) on what is still unmatched
unmatched new findings  -> new
unmatched old records   -> gone (prune candidates)
```

Each finding is paired at most once, and a record consumed by an early pass is not
available to a later one, so looser keys cannot steal a strict match. Passes run per
rule and per file, so the dict lookups keep the whole thing linear in the number of
findings: a 100k-entry baseline against a 100k-finding scan is one pass over each
side per key (four dict builds), plus the similarity pass, which is bounded (2.3).

Ambiguity: when two or more scan findings compete for one baseline record (a twin, a
pasted copy), the matcher pairs one and marks the match `ambiguous`. The default
output treats an ambiguous match as known (what every pairing scheme does; the study's
`duplicate_above` row); `--baseline-strict` treats it as new, which is the right
setting for a security gate: a pasted copy of a vulnerability then always fails the
build, at the cost of the original being reported too.

### 2.3 Similarity pass (edited lines)

Edited flagged lines are where every scheme fails (study: `line_text` 100%, `github`
87.4%, `codeguard` 74.8%, SonarQube 63.6% of such findings reported as new). After the
key passes, for each file pair and rule with unmatched findings on both sides, pair old
and new by the Jaccard similarity of their `stmt_tokens` (token sets, identifiers and
literals masked as in `ident`), accepting pairs with similarity >= 0.6, highest first,
closest line first on ties, each finding once. Bounded: a file rarely has more than a
handful of unmatched findings per rule; cap the pass at 64 x 64 candidates per
(file, rule) and skip beyond that.

The threshold is a design choice to be tuned on the study's development split and
reported with its held-out result; the study's own ground truth uses character-level
difflib similarity on whole lines, a different measure, so the two are not the same
rule in two places.

### 2.4 Rename awareness

The baseline records the commit it was created at (`"commit": "<sha>"`, when the
project root is a git repository). At scan time, if git is available and the baseline
has a commit, `git diff -M --name-status <commit>` gives renames (`R` lines) and the
matcher pairs those files. Without git or a commit (an exported scan, a tarball), the
content pairing in 2.2 runs instead. Both modes are evaluated in the harness, like
`sonar` and `sonar_branch`: the content pairing must accept at least what git's 50%
rule accepts on the corpus's 287 renamed-file findings.

Also from git: the baseline's `commit` lets `codeguard ci` pair against the baseline
even when it scans only changed files (`--diff`), because the records of unchanged
files are simply carried over as known.

### 2.5 Baseline file, schema 2

```json
{
  "version": 2,
  "scheme": "codeguard/v2",
  "created": "...", "tool_version": "2.3.0", "commit": "abc123" | null,
  "findings": [
    {"rule": "...", "file": "...", "line": 42, "scope": "...", "k": {...},
     "stmt_tokens": [...], "first_seen": "..."}
  ]
}
```

- `Baseline.load` reads both versions. A version-1 file is upgraded in memory: each
  entry becomes a record with `file`, `rule` and a single key `v1` (the old hash); the
  matcher's first pass then compares the scan's v1 hash (still computed) with it, and
  everything else is unmatched, which is exactly today's behaviour minus set membership.
  `baseline update` writes version 2 and fills the records from the current scan, so
  one `update` after upgrading CodeGuard converts the file.
- `baseline create`: as today, plus `commit` and the records.
- `baseline update`: runs the matcher; adds unmatched scan findings as new records;
  **replaces** the matched records with their current counterparts (new line, keys,
  tokens) keeping `first_seen`, so the baseline follows the code and the next match is
  the strict one again. Prints how many were added and how many followed.
- `baseline prune`: runs the matcher; drops unmatched records.
- The file is sorted by `(file, rule, line)` for stable diffs.

### 2.6 Output

- JSON: `fingerprint` keeps the v1 hash (consumers compare it as an opaque string;
  the VS Code extension uses it in tree-item ids). Add `identity: {scheme: "codeguard/v2", keys: {...}}`
  and, when a baseline was applied, `match: {"status": "known" | "new" | "ambiguous", "pass": "stmt" | ... }`.
- SARIF `partialFingerprints`: `{"codeguard/v1": ..., "codeguard/v2/stmt": ..., "codeguard/v2/nscope": ..., "codeguard/v2/ident": ..., "codeguard/v2/lh": ...}`.
  SARIF allows several named partial fingerprints and asks consumers to match on any
  equal one; GitHub code scanning uses its own `primaryLocationLineHash` and ignores
  the rest, so nothing changes for it.
- Terminal, GitHub annotations, JUnit: unchanged, plus `(ambiguous)` after
  `(baselined)` where it applies.
- Exit code: unchanged contract (`docs/exit-codes.md`); ambiguous matches gate only
  under `--baseline-strict` (new flag and `[codeguard] baseline_strict = true`).

### 2.7 Where the research harness plugs in

`research/finding_identity/trackers.py` gains `codeguard_v2_match(old, new)` that calls
the product matcher (`codeguard.engine.identity.match`) on `Observation` lists, and
`MATCHERS["codeguard_v2"]` points at it, like `sonar`. `RENAME_CHECKS["codeguard_v2_content"]`
wraps the content pairing of 2.2 so both rename modes are measured. The harness must
not re-implement any of it: the paper reports the shipped code.

Iteration plan (for the agent that implements this): add `--save-observations` to the
replay so a run stores each file version's findings (rule, line, col, message, and the
blob sha for the text); a `rescore` command then recomputes every scheme's outcomes
from that cache in minutes instead of re-running the analyzers. Tune the similarity
threshold and the tie-break order on a development split of the corpus (half the
repositories, drawn with a seed) and report the held-out half separately in the paper.

## 3. Compatibility

| who | risk | mitigation |
|---|---|---|
| users' `.codeguard-baseline.json` (v1) | must keep working | loaded and matched on the `v1` key; `baseline update` converts; nothing is silently reported as new |
| `fingerprint` in JSON / LSP / VS Code | consumers treat it as opaque | unchanged (still the v1 hash); new fields are additive |
| SARIF consumers | extra partialFingerprints | additive; the spec allows several |
| `codeguard/v1` suppressions by fingerprint | none exist (suppressions are inline comments) | |
| exit codes | `--baseline-strict` can newly fail a build | opt-in |
| performance | matcher over 100k findings | linear passes; similarity pass capped |
| `editors/vscode` | reads `fingerprint`, `baselined` counts, watches the baseline file | unchanged; its CHANGELOG needs no entry unless the LSP payload changes (adding `match` to the payload would need one, see `.github/workflows/ci.yml`) |

Tests to update: `tests/test_engine/test_baseline.py` (schema 2 round trip, v1 load and
upgrade, `updated_with` following matched findings, `pruned` through the matcher),
`tests/test_cli/test_ci.py` (`update`/`prune` messages, `--baseline-strict`),
`tests/test_cli/test_formatters.py` (SARIF `partialFingerprints` has five entries),
`tests/test_engine/test_identity_behaviour.py` (remove the `xfail` marks), and new
`tests/test_engine/test_identity.py` for the matcher (each pass, tie-breaking,
ambiguity, renames with and without git, the similarity cap).

Docs and changelog: `docs/baseline.md` (what "known" means, strict mode, upgrading),
`docs/output-formats.md` (new fields), `docs/architecture.md` (`engine/identity.py`),
`docs/ci.md` (strict mode for security gates), and a `changelog.d/<pr>.feature.md`
fragment (CI requires one for any `src/` change; see `changelog.d/README.md`). The
version bump is minor (2.3.0): the JSON schema and exit codes are additive.
