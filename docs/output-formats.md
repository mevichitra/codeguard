# Output formats

Select with `--format`.

## `human` (default)

Coloured terminal output: one header line per finding (`file:line:col [RULE] SEVERITY
title`), the offending source line with a caret, the fix suggestion, and a severity
summary.

## `json`

A JSON array of finding objects. Each object has `rule_id`, `title`, `description`,
`severity`, `category`, `location` (`file`, `line`, `col`, `end_line`, `end_col`),
`cwe`, `owasp`, `fix_suggestion`, `confidence`, and `suppressed`.

!!! note "Changing in v2.0"
    `--format json` becomes an envelope object — `{ version, tool, rules, results,
    summary }` — with a per-finding `fingerprint`. The current bare-array output stays
    available as `--format json-legacy` for one minor version.

## `sarif`

[SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/) — the format GitHub code
scanning and most analysis tooling understand. Includes a `rules[]` catalogue with
CWE/OWASP metadata and, for suppressed findings, `suppressions[]` entries.

```bash
codeguard scan src/ --format sarif -o codeguard.sarif
```

!!! note "Changing in v2.0"
    SARIF output gains `partialFingerprints` (stable across reformatting and line moves),
    `security-severity`, `helpUri`, and CWE taxonomy entries. v2.0 also adds `github`
    (Actions annotations), `rdjson` (reviewdog), and `junit` formats.
