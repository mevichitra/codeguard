# Baseline

A **baseline** freezes the findings that exist in your codebase today so CI only
fails on *new* problems. It is a small JSON file of finding fingerprints —
fingerprints are stable across reformatting and line moves, so a baselined
finding stays matched as the code around it changes.

## Create one

```bash
codeguard baseline create              # writes .codeguard-baseline.json
codeguard baseline create src/ -o ci/codeguard-baseline.json
```

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
`"baselined": true` field and SARIF emits a `suppressions` entry so GitHub code
scanning dismisses them.

## Maintain it

```bash
codeguard baseline update   # add findings that have appeared since (keeps first_seen)
codeguard baseline prune    # drop entries whose finding no longer occurs
```

A good workflow: `create` once, `prune` on a schedule, and let PRs drive the
count down — never `update` to sweep new findings under the rug.
