# Finding identity

CodeGuard has to decide, for every finding of a scan, whether it is one it reported
before. [Baselines](baseline.md) depend on that decision, and so do the SARIF
fingerprints that let code-scanning services keep an alert open across commits.
Scheme `codeguard/v2` makes the decision with a small record of keys per finding and
a matcher; the older single hash, `codeguard/v1`, is still emitted for consumers
that treat it as an opaque id.

## The identity record

Every key is built from the **statement** the parser says contains the flagged line,
never from the line text alone, the file path or the message. Each is a 16-character
hash.

| key | built from | survives |
|---|---|---|
| `stmt` | rule, enclosing function or class, the statement with literals masked and comments and whitespace removed | reformatting, line moves, changed literals |
| `nscope` | rule, the same statement without the scope | a renamed enclosing function, extraction into a helper |
| `ident` | rule, scope, the statement with identifiers masked (keywords, attribute names and call names kept) | a renamed local |
| `body` | rule, parent scope, the function body with its own name removed; only for a finding on a function or class header | a renamed function, a changed signature |
| `lh` | rule, the raw line without whitespace | nothing: pairs renamed files by content |
| `ctx_prev`, `ctx_next` | the normalized lines before and after the statement | not keys: they break ties between equal candidates |
| `v1` | the `codeguard/v1` hash (rule, path, scope, the flagged line) | kept for old baselines |

The statement comes from the AST for Python and from the tree-sitter tree for
JavaScript and TypeScript, which now also gives JavaScript findings a scope
(`Class.method`, `handler`, the name an arrow function is assigned to).

## The matcher

`codeguard.engine.matcher.match(old, new, config)` pairs two lists of records, one to
one, pass by pass: `stmt`, `v1`, `nscope`, `body`, `ident`, then a similarity pass
that pairs leftovers of one rule whose token sets have a Jaccard similarity of at
least 0.7. A record paired by an early pass is not available to a later one, so a
loose key never steals a strict match. Inside a group of equal keys the tie is broken
by the neighbouring lines (the following line counts more, so a copy pasted directly
above a finding leaves the original the better candidate), then by line distance; a
pairing that line distance alone decided is **ambiguous**.

Two guards keep the loose passes honest. The identifier pass and the similarity pass
refuse to follow an identifier that still exists in the other version's scope:
`eval(b)` next to a surviving `a` is a new statement, `eval(payload)` after `data`
vanished from the function is the old one. And the similarity pass skips a group with
more than 64 unmatched findings on either side, so the matcher stays linear in the
number of findings.

Every threshold is a field of `MatchConfig`: `passes`, `similarity_threshold`
(0.7), `similarity_cap` (64), `group_cap` (64), `context_tiebreak`,
`same_scope_first`.

## Files

Findings are matched file by file. The same path pairs first; then the renames git
reports between the commit the baseline records and the working tree; then, for
what is still unpaired, a removed and an added file with the same extension whose
findings' `lh` keys overlap by at least 50% (`PairConfig.content_threshold`).

## In the output

- JSON: `identity` (the scheme, the scope and the keys) on every finding, and
  `match` (`status`: `known`, `ambiguous` or `new`; `pass`; `score`) when a baseline
  was applied. `fingerprint` is still the v1 hash.
- SARIF: `partialFingerprints` carries `codeguard/v1` plus `codeguard/v2/stmt`,
  `/nscope`, `/ident`, `/lh` and, for header findings, `/body`.
- Terminal: `(ambiguous)` after a finding the matcher had to guess about.

## How well it works

The scheme was designed from the finding-identity study in
`research/finding_identity/`, which replays commit histories of 35 open-source
applications and scores identity schemes against a line-diff ground truth. The study
measures the shipped code: its harness imports this matcher.
