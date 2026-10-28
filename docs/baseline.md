# Baseline

A **baseline** freezes the findings that exist in your codebase today so CI only
fails on *new* problems. It is a JSON file with one record per finding: the rule,
the file and line, and the finding's [identity](identity.md), a set of keys built
from the statement the finding sits in. At scan time each current finding is
paired with at most one baseline record, so a baselined finding stays matched as
the code around it changes, and a second copy of it is reported.

## Create one

```bash
codeguard baseline create              # writes .codeguard-baseline.json
codeguard baseline create src/ -o ci/codeguard-baseline.json
```

When the project is a git repository the file records the commit it was taken at.
Later scans use it to follow renamed files (`git diff -M`); without git, renamed
files are paired by their content.

## Use it

```bash
codeguard scan . --baseline .codeguard-baseline.json
```

Or point at it from `codeguard.toml` so every run picks it up:

```toml
[codeguard]
baseline = ".codeguard-baseline.json"
```

Baselined findings are **hidden** from the default output and never affect the
exit code. `--show-suppressed` reveals them (tagged `(baselined)`); JSON keeps a
`"baselined": true` field plus a `match` object saying which pass paired the
finding, and SARIF emits a `suppressions` entry so GitHub code scanning dismisses
them.

## What "known" means

A current finding is known when the matcher pairs it with a baseline record of the
same rule in the same file (or the file it was renamed from). The matcher tries the
identity keys from strictest to loosest, and a record pairs with one finding only:

1. the same statement in the same function or class;
2. the same statement anywhere in the file (the function was renamed or the
   statement was extracted into a helper);
3. for a finding on a function header, the same body (the signature changed);
4. the same statement shape with identifiers masked (a local was renamed, and the
   old name is gone from the scope);
5. a statement of the same rule whose tokens are at least 70% the same (the line
   was edited).

Baselines written by CodeGuard 2.2 and earlier hold only the old `codeguard/v1`
fingerprint per entry. They still load and match on that fingerprint; run
`codeguard baseline update` once to convert the file to the new schema.

### Ambiguous matches and strict mode

When two or more current findings have the same key as one record (a statement
pasted twice, a copy of a vulnerable line), the matcher pairs the one whose
neighbouring lines agree with the record, or the nearest one, and marks the match
*ambiguous*. By default an ambiguous match counts as known, like any other. With
`--baseline-strict` (or `baseline_strict = true` in `codeguard.toml`) an ambiguous
match is reported as new, so a pasted copy of a baselined vulnerability always
fails the build, at the cost of the original being reported with it. Use it for
security gates.

## Maintain it

```bash
codeguard baseline update   # follow moved or edited findings; add the new ones
codeguard baseline prune    # drop entries whose finding no longer occurs
```

`update` replaces each matched record with its current finding (the line, the keys)
while keeping `first_seen`, so the next match is the strict one again, and adds
records for findings it could not pair. `prune` keeps only the records that still
pair with a finding.

A good workflow: `create` once, `prune` on a schedule, and let PRs drive the
count down. Run `update` after a large refactoring so the records follow the
code; never use it to sweep new findings under the rug.
