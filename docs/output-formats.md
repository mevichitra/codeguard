# Output formats

Select with `--format` (on `scan` and `ci`). Suppressed and baselined findings
are omitted from every format unless `--show-suppressed` is given.

## `human` (default)

Coloured terminal output: one header line per finding (`file:line:col [RULE]
SEVERITY  title`), the offending source line with a caret, the fix suggestion,
and a severity summary.

## `json`

An envelope object:

```json
{
  "schema_version": "1",
  "tool": { "name": "CodeGuard", "version": "…" },
  "rules":   [ { "id": "CG-SEC-001", "title": "…", "severity": "high", "cwe": "CWE-89", … } ],
  "results": [ { "rule_id": "…", "location": {…}, "fingerprint": "…", "identity": {…}, "baselined": false, "match": {…}, … } ],
  "summary": { "findings": 3, "by_severity": {"high": 3}, "suppressed": 0 }
}
```

`fingerprint` is the `codeguard/v1` hash; `identity` holds the `codeguard/v2` keys
and `match` (present when a baseline was applied) says whether the finding is
`known`, `ambiguous` or `new` and which matcher pass paired it. See
[Finding identity](identity.md).

`--format json-legacy` emits the pre-2.0 bare array (deprecated, one minor version).

## `sarif`

[SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/) for GitHub code
scanning and other tooling. Includes a `rules[]` catalogue with `helpUri`,
`security-severity`, and CWE taxonomy tags; every result carries
`partialFingerprints` (`codeguard/v1` plus the `codeguard/v2/*` keys, stable across
reformatting, line moves and renames) and, when suppressed or baselined, a
`suppressions[]` entry.

```bash
codeguard scan src/ --format sarif -o codeguard.sarif
```

## `github`

GitHub Actions workflow-command annotations (`::error file=…,line=…::message`),
one per finding — shows on the PR diff without a SARIF upload. This is the
default for `codeguard ci`.

## `rdjson`

[Reviewdog Diagnostic JSON](https://github.com/reviewdog/reviewdog) — pipe into
`reviewdog -f=rdjson -reporter=github-pr-review` for inline PR comments on
changed lines only.

## `junit`

JUnit XML — one `<testcase>` per finding (`<failure>` for active, `<skipped>` for
baselined). Feeds CI test-report dashboards.
